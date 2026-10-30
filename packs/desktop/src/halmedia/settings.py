"""Settings for halmedia: the [media] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

TABLE = config.register(
    config.Table(
        "media",
        (
            config.Key("music_dirs", list, ["~/Music"], doc="Folders searched for music"),
            config.Key("player", str, "vlc", doc="Preferred media player; empty means auto"),
        ),
        owner="hal-desktop",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)
