"""Settings for halscreen: the [screen] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "screen",
        (config.Key("keep", int, 20, doc="Screenshots kept before the oldest are deleted"),),
        owner="hal-desktop",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def shared() -> Mapping[str, object]:
    """Returns the shared `[hal]` table (models, vault, user name)."""
    return config.hal()


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "screen"
    path.mkdir(parents=True, exist_ok=True)
    return path
