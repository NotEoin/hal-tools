"""Settings and files for hal-telegram.

The [telegram] table of the shared config holds this module's settings, read through
`halkit.config`. The bot token, the paired chat and the pending pairing code are files beside
that config (`telegram-*` in `halkit.paths.config_dir()`), which hal-notify also reads.
`HAL_CONFIG` moves all of them, which is how the tests run in a sandbox.
"""

import os
from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

ROOT = Path(__file__).resolve().parents[1]  # this checkout
ECOSYSTEM = ROOT.parents[1]  # hal-ecosystem, when this sits in extensions/

TABLE = config.register(
    config.Table(
        "telegram",
        (
            config.Key("persona", str, "", doc="Persona; empty means [brain].persona"),
            config.Key(
                "model", str, "", doc="Model; empty means [brain].model, then [hal].chat_model"
            ),
            config.Key(
                "whisper_model", str, "small.en", doc="faster-whisper model for voice notes"
            ),
            config.Key(
                "whisper_device", str, "cpu", choices=("cpu", "cuda", "auto"), doc="Whisper device"
            ),
            config.Key("voice_replies", bool, True, doc="Answer voice notes with a voice note"),
            config.Key("voice_root", str, "", doc="hal-voice checkout; empty means the sibling"),
        ),
        owner="hal-comms",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def state_dir() -> Path:
    """Returns the directory that holds the token, chat and pairing files."""
    return paths.config_file().parent


def token_file() -> Path:
    """Returns the bot token file."""
    return state_dir() / "telegram-token"


def chat_file() -> Path:
    """Returns the paired chat id file."""
    return state_dir() / "telegram-chat"


def pairing_file() -> Path:
    """Returns the pending pairing code file."""
    return state_dir() / "telegram-pairing"


def write_private(path: Path, text: str) -> None:
    """Writes a file only its owner can read."""
    config.write_private(path, text)


def find_core() -> Path | None:
    """Returns core hal: HAL_CORE, else <ecosystem>/core/hal, else [hal].core; None when missing."""
    legacy = config.read_toml(paths.config_file()).get("hal", {})
    for c in (
        os.environ.get("HAL_CORE"),
        str(ECOSYSTEM / "core" / "hal"),
        legacy.get("core") if isinstance(legacy, dict) else None,
    ):
        if c and (Path(c).expanduser() / "halcore" / "brain.py").is_file():
            return Path(c).expanduser().resolve()
    return None


def find_voice() -> Path | None:
    """Returns the hal-voice checkout (`voice_root`, else the sibling); None when missing."""
    for c in (settings()["voice_root"], str(ROOT.parent / "hal-voice")):
        if c and (Path(str(c)).expanduser() / "halvoice").is_dir():
            return Path(str(c)).expanduser().resolve()
    return None
