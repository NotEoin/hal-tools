"""A small Agent Client Protocol client: JSON-RPC lines over a pair of text streams.

The Telegram bridge talks to `hal acp --channel telegram --toolset assistant` through this
client and never runs a brain itself (RESOLUTIONS A1, B9). A reader thread feeds a queue, so
every wait has a timeout; `prompt` answers permission requests through a callback and returns
the reply text.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from typing import IO, Any

log = logging.getLogger("hal-telegram")

PROTOCOL_VERSION = 1  # ACP protocol version this client speaks
INIT_TIMEOUT_S = 30.0  # `initialize` and `session/new` answer at once; a hung agent must not stall
CLOSE_WAIT_S = 5.0  # time the agent gets to exit after its stdin closes
CANCELLED = {"outcome": {"outcome": "cancelled"}}

PermissionHandler = Callable[[dict[str, Any]], str | None]


class AcpError(RuntimeError):
    """The agent answered a request with a JSON-RPC error."""


class AcpClosed(AcpError):
    """The agent's output ended, so it has exited."""


class AcpTimeout(AcpError):
    """A turn ran past its time limit; `session/cancel` was sent."""


class AcpClient:
    """One ACP connection: `reader` carries the agent's lines, `writer` ours."""

    def __init__(self, reader: IO[str], writer: IO[str], proc: subprocess.Popen | None = None):
        self._writer = writer
        self._proc = proc
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._next_id = 0
        self._write_lock = threading.Lock()
        threading.Thread(target=self._pump, args=(reader,), daemon=True).start()

    @classmethod
    def spawn(cls, argv: list[str]) -> AcpClient:
        """Starts the agent process and connects to its stdio."""
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert proc.stdin is not None and proc.stdout is not None  # noqa: S101 - PIPE was requested
        return cls(proc.stdout, proc.stdin, proc)

    def _pump(self, reader: IO[str]) -> None:
        for line in reader:
            self._lines.put(line)
        self._lines.put(None)

    @property
    def alive(self) -> bool:
        """True until the agent's output has ended."""
        return not (self._proc is not None and self._proc.poll() is not None)

    def _send(self, message: dict[str, Any]) -> None:
        with self._write_lock:
            try:
                self._writer.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
                self._writer.flush()
            except (OSError, ValueError) as exc:
                raise AcpClosed(f"agent is gone: {exc}") from exc

    def _read(self, deadline: float) -> dict[str, Any]:
        while True:
            try:
                line = self._lines.get(timeout=max(deadline - time.monotonic(), 0.0))
            except queue.Empty:
                raise TimeoutError from None
            if line is None:
                self._lines.put(None)
                raise AcpClosed("the agent exited")
            try:
                message = json.loads(line)
            except ValueError:
                log.warning("ignored a non-JSON line from the agent")
                continue
            if isinstance(message, dict):
                return message

    def request(
        self,
        method: str,
        params: dict[str, Any],
        timeout_s: float,
        on_permission: PermissionHandler | None = None,
        chunks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sends a request and returns its result; serves the agent's calls while waiting."""
        self._next_id += 1
        rid = self._next_id
        self._send({"id": rid, "method": method, "params": params})
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                message = self._read(deadline)
            except TimeoutError:
                self._send(
                    {"method": "session/cancel", "params": {"sessionId": params.get("sessionId")}}
                )
                raise AcpTimeout(f"{method} timed out after {timeout_s:.0f} s") from None
            if message.get("id") == rid and "method" not in message:
                if "error" in message:
                    raise AcpError(f"{method}: {message['error']}")
                return message.get("result") or {}
            self._serve(message, on_permission, chunks)

    def _serve(
        self,
        message: dict[str, Any],
        on_permission: PermissionHandler | None,
        chunks: list[str] | None,
    ) -> None:
        method = message.get("method")
        params = message.get("params") or {}
        if method == "session/update":
            update = params.get("update") or {}
            content = update.get("content") or {}
            if chunks is not None and update.get("sessionUpdate") == "agent_message_chunk":
                if content.get("type") == "text":
                    chunks.append(str(content.get("text", "")))
        elif method == "session/request_permission" and "id" in message:
            option = on_permission(params) if on_permission else None
            outcome = (
                {"outcome": {"outcome": "selected", "optionId": option}} if option else CANCELLED
            )
            self._send({"id": message["id"], "result": outcome})
        elif "id" in message and method:
            self._send({"id": message["id"], "error": {"code": -32601, "message": "not supported"}})

    def initialize(self) -> None:
        """Opens the connection; the client offers no file or terminal access."""
        self.request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "clientCapabilities": {}},
            INIT_TIMEOUT_S,
        )

    def new_session(self, cwd: str) -> str:
        """Returns the id of a fresh session."""
        result = self.request("session/new", {"cwd": cwd, "mcpServers": []}, INIT_TIMEOUT_S)
        return str(result["sessionId"])

    def prompt(
        self,
        session: str,
        text: str,
        timeout_s: float,
        on_permission: PermissionHandler | None = None,
    ) -> str:
        """Sends one user turn and returns the agent's reply text; raises `AcpTimeout` on expiry."""
        chunks: list[str] = []
        params = {"sessionId": session, "prompt": [{"type": "text", "text": text}]}
        self.request("session/prompt", params, timeout_s, on_permission, chunks)
        return "".join(chunks).strip()

    def close(self) -> None:
        """Closes the agent's stdin and stops the process if it lingers."""
        try:
            self._writer.close()
        except OSError:
            pass
        if self._proc is not None:
            try:
                self._proc.wait(CLOSE_WAIT_S)
            except subprocess.TimeoutExpired:
                self._proc.kill()
