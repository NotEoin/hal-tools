"""Settings and files for hal-telegram.

The [telegram] table of ~/.config/hal/config.toml holds this module's settings;
the bot token, the paired chat and the pending pairing code are files beside
that config (~/.config/hal/telegram-*), which hal-notify also reads. HAL_CONFIG
moves all of them, which is how the tests run in a sandbox. Stdlib only.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

SECTION = "telegram"
DEFAULTS: dict = {
    "persona": "",                  # empty = [brain].persona, else core hal's built-in persona
    "model": "",                    # empty = [brain].model, else [hal].chat_model
    "whisper_model": "small.en",    # faster-whisper model for voice notes
    "whisper_device": "cpu",        # cpu | cuda | auto
    "voice_replies": True,          # answer voice notes and /brief with a voice note too (needs hal-voice)
}
JOBHUNT_DEFAULT = "~/src/employment-helper"

ROOT = Path(__file__).resolve().parents[1]      # this checkout
ECOSYSTEM = ROOT.parents[1]                     # hal-ecosystem, when this sits in extensions/


def config_path() -> Path:
    return Path(os.environ.get("HAL_CONFIG", "~/.config/hal/config.toml")).expanduser()


def _file() -> dict:
    try:
        return tomllib.loads(config_path().read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def settings() -> dict:
    """Returns this module's settings merged over its defaults."""
    return {**DEFAULTS, **_file().get(SECTION, {})}


def state_dir() -> Path:
    return config_path().parent


def token_file() -> Path:
    return state_dir() / "telegram-token"


def chat_file() -> Path:
    return state_dir() / "telegram-chat"


def pairing_file() -> Path:
    return state_dir() / "telegram-pairing"


def write_private(path: Path, text: str) -> None:
    """Writes a file only its owner can read."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    path.chmod(0o600)


def jobhunt_root() -> Path:
    """Returns the jobhunt checkout: [jobs].jobhunt_root, else [jobs].jobhunt (hal-jobs' key), else the default."""
    jobs = _file().get("jobs", {})
    return Path(jobs.get("jobhunt_root") or jobs.get("jobhunt") or JOBHUNT_DEFAULT).expanduser()


def find_core() -> Path | None:
    """Returns core hal: HAL_CORE, else <ecosystem>/core/hal, else [hal].core; None when missing."""
    for c in (os.environ.get("HAL_CORE"), str(ECOSYSTEM / "core" / "hal"), _file().get("hal", {}).get("core")):
        if c and (Path(c).expanduser() / "halcore" / "brain.py").is_file():
            return Path(c).expanduser().resolve()
    return None


def find_voice() -> Path | None:
    """Returns the hal-voice checkout beside this one, or [telegram].voice_root; None when missing."""
    for c in (settings().get("voice_root"), str(ROOT.parent / "hal-voice")):
        if c and (Path(c).expanduser() / "halvoice").is_dir():
            return Path(c).expanduser().resolve()
    return None
