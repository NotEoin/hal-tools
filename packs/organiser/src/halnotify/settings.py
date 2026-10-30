"""Settings for hal-notify: the [notify] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "notify",
        (
            config.Key("channels", list, ["desktop", "phone"], doc="Default delivery channels"),
            config.Key("quiet_from", int, 22, doc="Hour quiet hours start"),
            config.Key("quiet_until", int, 8, doc="Hour quiet hours end"),
            config.Key(
                "ntfy_topic", str, "", doc="ntfy topic for the phone channel; empty disables it"
            ),
            config.Key("ntfy_server", str, "https://ntfy.sh", doc="ntfy server URL"),
        ),
        owner="hal-organiser",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "notify"
    path.mkdir(parents=True, exist_ok=True)
    return path
