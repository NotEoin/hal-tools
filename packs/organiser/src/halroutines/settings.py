"""Settings for hal-routines: the [routines] table of the shared config, read through
`halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

IDLE_MINUTES = 15
# Built-in scenes; scenes saved by asking Hal live in the module database.
SCENES: dict[str, list[dict]] = {
    "focus": [
        {"tool": "notify_dnd", "args": {"minutes": 90}},
        {"tool": "desktop_banners", "args": {"on": "off"}},
        {"tool": "media_control", "args": {"action": "pause"}},
        {"tool": "rgb_colour", "args": {"colour": "warm white", "brightness": 40}},
        {"tool": "clock_pomodoro", "args": {"action": "start"}},
    ],
    "relax": [
        {"tool": "notify_dnd", "args": {"minutes": 0}},
        {"tool": "desktop_banners", "args": {"on": "on"}},
        {"tool": "rgb_effect", "args": {"effect": "breathing"}},
        {"tool": "desktop_night_light", "args": {"on": "on"}},
    ],
    "goodnight": [
        {"tool": "media_control", "args": {"action": "pause"}},
        {"tool": "rgb_off", "args": {}},
        {"tool": "briefing_deliver", "args": {"kind": "evening", "speak": False}},
        {"tool": "desktop_lock", "args": {}},
    ],
    "away": [
        {"tool": "media_control", "args": {"action": "pause"}},
        {"tool": "rgb_colour", "args": {"colour": "hal red", "brightness": 10}},
        {"tool": "desktop_lock", "args": {}},
    ],
    "movie": [
        {"tool": "notify_dnd", "args": {"minutes": 150}},
        {"tool": "rgb_colour", "args": {"colour": "navy", "brightness": 15}},
        {"tool": "desktop_night_light", "args": {"on": "on"}},
    ],
}

TABLE = config.register(
    config.Table(
        "routines",
        (
            config.Key(
                "idle_minutes", int, IDLE_MINUTES, doc="Idle minutes before idle routines run"
            ),
            config.Key("scenes", dict, SCENES, doc="Built-in scenes: name to a list of tool steps"),
        ),
        owner="hal-organiser",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "routines"
    path.mkdir(parents=True, exist_ok=True)
    return path
