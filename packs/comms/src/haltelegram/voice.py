"""Voice notes through the `hal-voice` CLI: it reads them and speaks the replies.

The bridge never loads a speech model itself (Decision D19). Without `hal-voice` on `PATH` it
answers "voice notes need hal-voice" and stays a text bot.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from hal_comms import proc

from . import settings as config

TRANSCRIBE_TIMEOUT_S = 300.0  # spec 08: a long note on a CPU model
TTS_TIMEOUT_S = 120.0  # one reply, spoken
FFMPEG_TIMEOUT_S = 60.0  # a Telegram voice note is seconds of audio
NEEDS_VOICE = "voice notes need hal-voice"


class VoiceUnavailable(RuntimeError):
    """`hal-voice` is not installed or could not read the note."""


def transcribe(audio: Path) -> str:
    """Returns the words in a voice note; raises `VoiceUnavailable` without a working hal-voice."""
    if shutil.which("hal-voice") is None:
        raise VoiceUnavailable(NEEDS_VOICE)
    try:
        done = proc.completed(
            ["hal-voice", "transcribe-file", str(audio), "--json"], timeout=TRANSCRIBE_TIMEOUT_S
        )
    except (OSError, proc.ProcTimeout) as exc:
        raise VoiceUnavailable(f"hal-voice could not read that note: {exc}") from exc
    if done.returncode:
        raise VoiceUnavailable("hal-voice could not read that note")
    try:
        data = json.loads(done.stdout)
    except ValueError as exc:
        raise VoiceUnavailable("hal-voice gave an unreadable answer") from exc
    return str(data.get("text", "")).strip() if isinstance(data, dict) else ""


def synthesise(text: str, workdir: Path) -> Path | None:
    """Returns an Opus voice note of `text`, or None when voice replies are off or fail."""
    if not config.settings()["voice_replies"] or shutil.which("hal-voice") is None:
        return None
    wav, ogg = workdir / "reply.wav", workdir / "reply.ogg"
    try:
        spoken = proc.completed(
            ["hal-voice", "tts", "--out", str(wav), text], timeout=TTS_TIMEOUT_S
        )
        if spoken.returncode:
            return None
        done = proc.completed(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(wav),
                "-c:a",
                "libopus",
                "-b:a",
                "48k",
                str(ogg),
            ],
            timeout=FFMPEG_TIMEOUT_S,
        )
    except (OSError, proc.ProcTimeout):
        return None
    return None if done.returncode else ogg
