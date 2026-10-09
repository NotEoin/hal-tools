"""Settings for hal-rgb: the [rgb] table of ~/.config/hal/config.toml over DEFAULTS.

The shared [hal] table supplies the vault path and the local model settings.
"""
import os
import tomllib
from pathlib import Path

SECTION = "rgb"
DEFAULTS: dict = {
    "host": "127.0.0.1",
    "port": 6742,
    "follow_device": "",        # lights that show Hal's state; empty means all
    # Colours for Hal's states, used by rgb_state and by hal-voice when lights follow Hal.
    "states": {
        "idle": {"colour": "hal red", "brightness": 25},
        "listening": {"colour": "hal red", "brightness": 100},
        "thinking": {"colour": "amber", "brightness": 60},
        "speaking": {"colour": "hal red", "brightness": 80},
        "alert": {"colour": "white", "brightness": 100},
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
