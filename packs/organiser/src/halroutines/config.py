"""Settings for hal-routines: the [routines] table of ~/.config/hal/config.toml over DEFAULTS.

The shared [hal] table supplies the vault path and the local model settings.
"""

import os
import tomllib
from pathlib import Path

SECTION = "routines"
DEFAULTS: dict = {
    "idle_minutes": 15,
    # Built-in scenes; scenes saved by asking Hal live in the module's database.
    "scenes": {
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
    },
}
SHARED = {
    "vault": "~/Documents/vaults/Hal",
    "ollama_url": "http://localhost:11434",
    "chat_model": "qwen3.5:9b",
    "fast_model": "qwen3.5:4b",
    "embed_model": "embeddinggemma",
    "vision_model": "qwen3-vl:8b",
}


def config_path() -> Path:
    """Returns the shared config file; HAL_CONFIG overrides it, read on every call."""
    return Path(os.environ.get("HAL_CONFIG", "~/.config/hal/config.toml")).expanduser()


def _file() -> dict:
    try:
        return tomllib.loads(config_path().read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def settings() -> dict:
    """Returns this module's settings merged over its defaults."""
    return {**DEFAULTS, **_file().get(SECTION, {})}


def shared() -> dict:
    """Returns the ecosystem-wide settings."""
    return {**SHARED, **_file().get("hal", {})}


def vault() -> Path:
    return Path(shared()["vault"]).expanduser()


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    base = Path(os.environ.get("HAL_DATA", "~/.local/share/hal")).expanduser()
    path = base / SECTION
    path.mkdir(parents=True, exist_ok=True)
    return path
