"""Voice notes: faster-whisper to read them, hal-voice to answer in HAL's voice.

Both live in hal-voice's virtualenv, which the service runs under when hal-voice
is installed. Without them the bridge still works in text.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hal_comms import proc

from . import settings as config

FFMPEG_TIMEOUT_S = 60.0  # a Telegram voice note is seconds of audio
NEEDS_VOICE = "Voice notes need hal-voice installed (hal ext add voice)."

_model = None


class VoiceUnavailable(RuntimeError):
    pass


def transcribe(audio: Path) -> str:
    """Returns the words in a voice note; raises VoiceUnavailable without faster-whisper."""
    global _model
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise VoiceUnavailable(NEEDS_VOICE) from e
    if _model is None:
        s = config.settings()
        _model = WhisperModel(
            s["whisper_model"],
            device=s["whisper_device"],
            compute_type="int8" if s["whisper_device"] == "cpu" else "default",
        )
    segments, _ = _model.transcribe(str(audio), language="en", beam_size=1, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


def synthesise(text: str, workdir: Path) -> Path | None:
    """Returns an Opus voice note in HAL's voice, or None if hal-voice is unavailable."""
    if not config.settings()["voice_replies"]:
        return None
    root = config.find_voice()
    if root is None:
        return None
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        import soundfile
        from halvoice import tts

        audio, sr = tts.synth(text)
    except Exception:  # noqa: BLE001 - a voice reply is optional; the text is always sent
        return None
    wav, ogg = workdir / "reply.wav", workdir / "reply.ogg"
    soundfile.write(wav, audio, sr)
    try:
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
    if done.returncode:
        return None
    return ogg
