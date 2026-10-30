"""Settings for hal-briefing: the [briefing] table of the shared config (`halkit.config`).

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "briefing",
        (
            config.Key(
                "name", str, "", doc="How the briefing addresses you; empty uses [hal].user_name"
            ),
        ),
        owner="hal-organiser",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "briefing"
    path.mkdir(parents=True, exist_ok=True)
    return path
