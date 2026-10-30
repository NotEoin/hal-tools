"""Settings and files for hal-telegram.

The [telegram] table of the shared config holds this module's settings, read through
`halkit.config`. The bot token, the paired chat and the pending pairing code are files beside
that config (`telegram-*` in `halkit.paths.config_dir()`), which hal-notify also reads.
`HAL_CONFIG` moves all of them, which is how the tests run in a sandbox.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "telegram",
        (
            config.Key("voice_replies", bool, True, doc="Answer voice notes with a voice note"),
            config.Key("turn_timeout_s", int, 600, doc="Seconds a chat turn may take"),
        ),
        owner="hal-comms",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def work_dir() -> Path:
    """Returns the empty directory used as the ACP session `cwd`; `hal acp` replaces it."""
    path = paths.data_dir() / "telegram" / "work"
    path.mkdir(parents=True, exist_ok=True)
    return path


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
