"""Settings for halrgb: the [rgb] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

STATES_DEFAULT: dict = {
    "idle": {"colour": "hal red", "brightness": 25},
    "listening": {"colour": "hal red", "brightness": 100},
    "thinking": {"colour": "amber", "brightness": 60},
    "speaking": {"colour": "hal red", "brightness": 80},
    "alert": {"colour": "white", "brightness": 100},
}

TABLE = config.register(
    config.Table(
        "rgb",
        (
            config.Key("host", str, "127.0.0.1", doc="OpenRGB server host"),
            config.Key("port", int, 6742, doc="OpenRGB server port"),
            config.Key("follow_device", str, "", doc="Lights that show Hal state; empty means all"),
            config.Key(
                "states", dict, STATES_DEFAULT, doc="Colour and brightness for each Hal state"
            ),
        ),
        owner="hal-desktop",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)
