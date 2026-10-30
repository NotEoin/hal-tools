"""The Telegram bridge: pairing, commands, and chat answered by core Hal's brain.

The bot answers one chat only. Until a chat is paired it shows a pairing code as
a desktop notification; sending `/pair <code>` from Telegram saves that chat.
Free text and voice notes go to a halcore Brain(channel="telegram") with the
tools of every installed extension, one Brain per chat, kept until /reset.
"""

from __future__ import annotations

import logging
import secrets
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path

from hal_comms import proc

from . import settings as config
from . import voice
from .jobs import Jobs

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

NO_MODEL = "The local model isn't answering, so I can only take commands right now.\n\n" + HELP


def parse(text: str) -> tuple[str | None, str]:
    """Splits "/cmd@bot arg" into ("/cmd", "arg"); plain text gives (None, text)."""
    text = (text or "").strip()
    if not text.startswith("/"):
        return None, text
    command, _, arg = text.partition(" ")
    return command.split("@", 1)[0].lower(), arg.strip()


def load_core():
    """Puts core hal on sys.path; returns (Brain, halhub or None), or (None, None) without it."""
    core = config.find_core()
    if core is None:
        return None, None
    if str(core) not in sys.path:
        sys.path.insert(0, str(core))
    from halcore import hub
    from halcore.brain import Brain

    return Brain, hub.load()


def brain_factory() -> Callable[[], object] | None:
    """Returns a function making a telegram-channel Brain, or None without core hal."""
    brain_cls, _ = load_core()
    if brain_cls is None:
        return None
    s = config.settings()
    return lambda: brain_cls(
        channel="telegram", persona=s["persona"] or None, model=s["model"] or None, tools=True
    )


class Bridge:
    def __init__(self, bot, make_brain: Callable[[], object] | None = None, hub=None) -> None:
        self.bot = bot
        self.make_brain = make_brain
        self.jobs = Jobs(hub)
        self.brains: dict[int, object] = {}
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
            brain = self.brains.get(chat)
            if brain is not None:
                brain.reset()
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

    # -- the brain -----------------------------------------------------------------
    def brain_for(self, chat: int):
        """Returns this chat's Brain, making it on first use."""
        if chat not in self.brains:
            brain = self.make_brain()
            brain.on_deep_done = lambda text, c=chat: self.bot.send(
                c, "Background task finished.\n\n" + text[-3500:]
            )
            self.brains[chat] = brain
        return self.brains[chat]

    def chat_reply(self, chat: int, text: str) -> str:
        if self.make_brain is None:
            return "Core Hal isn't installed, so I can only take commands.\n\n" + HELP
        try:
            return self.brain_for(chat).reply(text) or "(no reply)"
        except (OSError, RuntimeError) as e:
            log.warning("brain failed: %s", e)
            return NO_MODEL


def run() -> int:
    """Polls Telegram and answers until stopped."""
    from .telegram import Telegram

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = config.token_file()
    if not token.exists():
        log.error("no bot token at %s; save one with: python3 -m haltelegram token <TOKEN>", token)
        return 1
    bot = Telegram(token.read_text().strip())
    _, hub = load_core()
    make_brain = brain_factory()
    if make_brain is None:
        log.warning(
            "core hal not found (HAL_CORE, the ecosystem layout or [hal].core): commands only"
        )
    bridge = Bridge(bot, make_brain, hub)
    bridge.announce_pairing()
    offset = None
    while True:
        try:
            updates = bot.call("getUpdates", offset=offset, timeout=50)
        except Exception as e:  # noqa: BLE001 - network drops are routine; retry
            log.warning("poll failed: %s", e)
            time.sleep(10)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                try:
                    bridge.handle(update["message"])
                except Exception:
                    log.exception("failed to handle message")
