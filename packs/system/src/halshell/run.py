"""The one capped subprocess runner of the shell module (REQ-PACK-22).

`halkit.proc.run` returns the whole output and has no cap, and a listing chosen by a model can be
unbounded (`cat /dev/zero`), so the shell tools read incrementally here. Design decisions:
no shell is ever started (argv list, `shell=False`); the child gets its own session so the whole
process group can be killed on a timeout or an overflow; stdin is `/dev/null` so nothing waits
for input; the environment is minimal so a secret in the caller's environment never reaches it.
"""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

READ_CHUNK = 65536  # bytes per read; small enough to notice an overflow quickly
POLL_SECONDS = 0.05  # selector wait so the deadline is checked often
ENV = {
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "LANG": "C.UTF-8",
    "PAGER": "cat",
    "SYSTEMD_PAGER": "",
    "SYSTEMD_COLORS": "0",
    "NO_COLOR": "1",
}
KILL_WAIT_SECONDS = 5  # a SIGKILLed group is reaped at once; this only bounds a stuck reap
ERRORS_CAP = 2000  # characters of stderr kept in a result


def minimal_env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """The fixed environment of a shell tool child, plus `extra`."""
    return {**ENV, "HOME": str(Path.home()), **(extra or {})}


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass  # the group already exited
    proc.wait(timeout=KILL_WAIT_SECONDS)


def capped(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: str | None,
    env: Mapping[str, str],
    max_output: int,
) -> dict:
    """Runs `argv` without a shell; returns exit code, output, errors and two flags.

    Output stops at `max_output` bytes (`truncated`) and the process group is killed then; a run
    past `timeout` seconds is killed too (`timed_out`, exit code -9).
    """
    proc = subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=dict(env),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    sel = selectors.DefaultSelector()
    if proc.stdout is None or proc.stderr is None:  # pragma: no cover - PIPE was requested
        raise RuntimeError("subprocess pipes missing")
    sel.register(proc.stdout, selectors.EVENT_READ, "out")
    sel.register(proc.stderr, selectors.EVENT_READ, "err")
    bufs = {"out": bytearray(), "err": bytearray()}
    deadline = time.monotonic() + timeout
    truncated = timed_out = False
    try:
        while sel.get_map():
            if time.monotonic() > deadline:
                timed_out = True
                break
            for key, _ in sel.select(POLL_SECONDS):
                chunk = os.read(key.fd, READ_CHUNK)
                if not chunk:
                    sel.unregister(key.fileobj)
                    continue
                bufs[key.data] += chunk
            if len(bufs["out"]) > max_output:
                truncated = True
                break
        if not (truncated or timed_out):
            try:  # both pipes closed; a child that lingers still counts against the deadline
                proc.wait(timeout=max(POLL_SECONDS, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        sel.close()
        if truncated or timed_out or proc.poll() is None:
            _kill_group(proc)
        proc.stdout.close()
        proc.stderr.close()
    code = -9 if timed_out else proc.returncode
    out = bytes(bufs["out"][:max_output]).decode("utf-8", "replace")
    err = bytes(bufs["err"]).decode("utf-8", "replace")[-ERRORS_CAP:]
    return {
        "exit_code": code,
        "output": out,
        "errors": err,
        "truncated": truncated,
        "timed_out": timed_out,
    }
