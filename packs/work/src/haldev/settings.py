"""Settings for haldev: the [dev] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config

TABLE = config.register(
    config.Table(
        "dev",
        (
            config.Key(
                "roots",
                list,
                ["~/src", "~/projects"],
                doc="Directories searched for git repositories; missing ones are skipped",
            ),
            config.Key("depth", int, 2, doc="How many levels below a root to search"),
        ),
        owner="hal-work",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def roots() -> list[Path]:
    """Returns the configured repository roots that exist, `~` expanded."""
    found = (Path(str(r)).expanduser() for r in settings()["roots"])
    return [r for r in found if r.is_dir()]


def shared() -> Mapping[str, object]:
    """Returns the shared `[hal]` table (models, vault, user name)."""
    return config.hal()
