"""The Telegram bridge: pairing, commands, and chat answered by `hal acp`.

The bot answers one chat only. Until a chat is paired it shows a pairing code as a desktop
notification; sending `/pair <code>` from Telegram saves that chat. Free text and voice notes
go to `hal acp --channel telegram --toolset assistant` as ACP prompts, so every turn runs in
the box and no brain lives in this process. Approvals appear as inline buttons.
"""

from __future__ import annotations

import logging
import secrets
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from hal_comms import proc

from . import settings as config
from . import voice
from .acp import AcpClient, AcpClosed, AcpError, AcpTimeout
from .jobs import HubClient, Jobs

log = logging.getLogger("hal-telegram")
NOTIFY_TIMEOUT_S = 10.0  # notify-send returns at once; a hung desktop bus must not stall startup

HELP = """Commands:
/status - what needs you, and the pipeline
/queue - the jobs ready to apply for (apply in Hal Employment)
/todo - your job to-do list; /todo <text> adds one
/discard <id> - take a job out of the queue
/brief - today's briefing, spoken
/jobs - best unreviewed matches, with ids
/shortlist <id> - mark a job to apply for
/pack <id> - draft the application pack (takes a few minutes)
/applied <id> - record that you applied
/reset - start a new conversation
Anything else is a message for Hal, who can use all of its tools. Voice notes work too."""

NO_AGENT = "Hal is not available, so I can only take commands right now.\n\n" + HELP
AGENT_ARGV = ["hal", "acp", "--channel", "telegram", "--toolset", "assistant"]
APPROVAL_TIMEOUT_S = 300.0  # how long a button request waits for a press (01 channel timeout)
LONG_DISPLAY = 3500  # a request longer than this is approved only from the CLI
POLL_S = 50  # Bot API long-poll seconds
APPROVAL_POLL_S = 5  # short polls while a turn waits for a button press
TOO_LONG = "that took too long"


def parse(text: str) -> tuple[str | None, str]:
    """Splits "/cmd@bot arg" into ("/cmd", "arg"); plain text gives (None, text)."""
    text = (text or "").strip()
    if not text.startswith("/"):
        return None, text
    command, _, arg = text.partition(" ")
    return command.split("@", 1)[0].lower(), arg.strip()


class Bridge:
    def __init__(self, bot, spawn_agent: Callable[[], AcpClient] | None = None, hub=None) -> None:
        self.bot = bot
        self.spawn_agent = spawn_agent
        self.agent: AcpClient | None = None
        self.sessions: dict[int, str] = {}
        self.jobs = Jobs(hub)
        self.offset: int | None = None
        self.backlog: list[dict] = []
        chat = config.chat_file()
        self.chat = int(chat.read_text().strip()) if chat.exists() else None
        self.pairing_code = None if self.chat else self._pairing_code()

    # -- pairing -------------------------------------------------------------------
    @staticmethod
    def _pairing_code() -> str:
        """Returns the saved pairing code, creating one on first run."""
        path = config.pairing_file()
        if path.exists():
            return path.read_text().strip()
        code = f"{secrets.randbelow(10**6):06d}"
        config.write_private(path, code)
        return code

    def announce_pairing(self) -> None:
        if self.pairing_code:
            message = f"Send /pair {self.pairing_code} to your Hal bot in Telegram."
            log.info(message)
            try:
                proc.completed(
                    ["notify-send", "-a", "Hal", "-u", "critical", "Pair Telegram", message],
                    timeout=NOTIFY_TIMEOUT_S,
                )
            except (OSError, proc.ProcTimeout) as exc:
                log.warning("pairing notice not shown: %s", exc)

    def _pair(self, chat: int, text: str) -> None:
        command, arg = parse(text)
        if command == "/pair" and arg == self.pairing_code:
            self.chat, self.pairing_code = chat, None
            config.write_private(config.chat_file(), str(chat))
            config.pairing_file().unlink(missing_ok=True)
            log.info("paired with chat %s", chat)
            self.bot.send(chat, "Paired. " + HELP)
        elif command == "/pair":
            log.info("rejected pairing attempt from chat %s", chat)
            self.bot.send(
                chat, "That code doesn't match. Use the code in the latest desktop notification."
            )

    def dispatch(self, update: dict) -> None:
        """Handles one Bot API update; a failure is logged, never raised."""
        if "message" in update:
            try:
                self.handle(update["message"])
            except Exception:
                log.exception("failed to handle message")

    # -- messages ------------------------------------------------------------------
    def handle(self, message: dict) -> None:
        chat = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if self.chat is None:
            self._pair(chat, text)
            return
        if chat != self.chat:
            log.warning("ignored message from unpaired chat %s", chat)
            return
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            spoken = "voice" in message
            if spoken:
                try:
                    text = voice.transcribe(
                        self.bot.download(message["voice"]["file_id"], workdir / "in.ogg")
                    )
                except voice.VoiceUnavailable as e:
                    self.bot.send(chat, str(e))
                    return
                self.bot.send(
                    chat, f"Heard: {text}" if text else "I couldn't make out any words in that."
                )
            if not text:
                return
            self.bot.typing(chat)
            reply = self.respond(chat, text)
            self.bot.send(chat, reply)
            if spoken or parse(text)[0] == "/brief":
                note = voice.synthesise(reply, workdir)
                if note:
                    self.bot.upload("sendVoice", "voice", note, chat_id=chat)

    def respond(self, chat: int, text: str) -> str:
        command, arg = parse(text)
        if command is None:
            return self.chat_reply(chat, text)
        if command in ("/start", "/help"):
            return HELP
        if command == "/reset":
            self.sessions.pop(chat, None)
            return "Starting afresh."
        simple = {
            "/status": self.jobs.status,
            "/brief": self.jobs.brief,
            "/jobs": self.jobs.matches,
            "/queue": self.jobs.queue,
        }
        if command in simple:
            return simple[command]()
        if command == "/todo":
            return self.jobs.todo(arg)
        with_id = {
            "/discard": self.jobs.discard,
            "/shortlist": self.jobs.shortlist,
            "/applied": self.jobs.applied,
        }
        if command in with_id and arg:
            return with_id[command](arg)
        if command == "/pack" and arg:
            if not self.jobs.has("jobs_pack"):
                return self.jobs.pack(arg)[0]
            threading.Thread(target=self._pack, args=(chat, arg), daemon=True).start()
            return "Drafting the pack. I'll send it when it's done."
        return HELP

    def _pack(self, chat: int, job: str) -> None:
        output, files = self.jobs.pack(job)
        self.bot.send(chat, output or "The pack command printed nothing.")
        for path in files:
            self.bot.upload("sendDocument", "document", path, chat_id=chat)

    # -- the agent -----------------------------------------------------------------
    def _session(self, chat: int) -> tuple[AcpClient, str]:
        """Returns the live agent and this chat's session, starting either when missing."""
        if self.agent is None or not self.agent.alive:
            self.sessions.clear()
            agent = self.spawn_agent()
            agent.initialize()
            self.agent = agent
        if chat not in self.sessions:
            self.sessions[chat] = self.agent.new_session(str(config.work_dir()))
        return self.agent, self.sessions[chat]

    def chat_reply(self, chat: int, text: str) -> str:
        """Runs one turn through `hal acp` and returns the reply, or why there was none."""
        if self.spawn_agent is None:
            return NO_AGENT
        try:
            agent, session = self._session(chat)
            reply = agent.prompt(
                session,
                text,
                float(config.settings()["turn_timeout_s"]),
                lambda params: self._approve(chat, params),
            )
        except AcpTimeout:
            return TOO_LONG
        except (AcpError, OSError) as e:
            log.warning("hal acp failed: %s", e)
            if isinstance(e, AcpClosed) or isinstance(e, OSError):
                self.agent = None
            return NO_AGENT
        return reply or "(no reply)"

    # -- approvals -----------------------------------------------------------------
    def _approve(self, chat: int, params: dict) -> str | None:
        """Shows a broker request with buttons; returns the chosen option id, else None."""
        meta = params.get("_meta") or {}
        if meta.get("hal/origin") != "broker" or not meta.get("hal/approval_id"):
            return None  # agent-originated requests are cancelled
        approval = str(meta["hal/approval_id"])
        display = str(meta.get("hal/display", ""))
        nonce = secrets.token_hex(4)
        prefix = f"apr:{approval}:{nonce}"
        options = params.get("options") or []
        allow = next((o["optionId"] for o in options if o.get("kind") == "allow_once"), None)
        deny = next(
            (o["optionId"] for o in options if str(o.get("kind", "")).startswith("reject")), None
        )
        buttons = [("Deny", f"{prefix}:deny")]
        text = display
        if len(display) > LONG_DISPLAY or allow is None:
            text = f"{display[:LONG_DISPLAY]}\n\nApprove with: hal approve {approval}"
        else:
            buttons.insert(0, ("Allow once", f"{prefix}:allow"))
        self.bot.send(chat, text, buttons=buttons)
        data = self._await_press(chat, prefix)
        if data == f"{prefix}:allow" and allow:
            return allow
        return deny

    def _await_press(self, chat: int, prefix: str) -> str | None:
        """Polls for a button press on `prefix`; other updates wait in the backlog."""
        deadline = time.monotonic() + APPROVAL_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                updates = self.bot.call("getUpdates", offset=self.offset, timeout=APPROVAL_POLL_S)
            except Exception as e:  # noqa: BLE001 - a dropped poll must not fail the turn
                log.warning("poll failed: %s", e)
                time.sleep(APPROVAL_POLL_S)
                continue
            for update in updates:
                self.offset = update["update_id"] + 1
                query = update.get("callback_query")
                if query is None:
                    self.backlog.append(update)
                    continue
                where = (query.get("message") or {}).get("chat", {}).get("id")
                data = str(query.get("data", ""))
                self.bot.answer_callback(query.get("id", ""))
                if where != chat or not data.startswith(prefix + ":"):
                    log.warning(
                        "ignored a button press from chat %s with data %r", where, data[:80]
                    )
                    continue
                return data
        return None


def run() -> int:
    """Polls Telegram and answers until stopped."""
    from .telegram import Telegram

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = config.token_file()
    if not token.exists():
        log.error("no bot token at %s; save one with: python3 -m haltelegram token <TOKEN>", token)
        return 1
    bot = Telegram(token.read_text().strip())
    bridge = Bridge(bot, lambda: AcpClient.spawn(AGENT_ARGV), HubClient())
    bridge.announce_pairing()
    while True:
        for update in bridge.backlog[:]:
            bridge.backlog.remove(update)
            bridge.dispatch(update)
        try:
            updates = bot.call("getUpdates", offset=bridge.offset, timeout=POLL_S)
        except Exception as e:  # noqa: BLE001 - network drops are routine; retry
            log.warning("poll failed: %s", e)
            time.sleep(10)
            continue
        for update in updates:
            bridge.offset = update["update_id"] + 1
            bridge.dispatch(update)
