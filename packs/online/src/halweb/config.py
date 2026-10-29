"""Settings for hal-web: the [web] table of ~/.config/hal/config.toml over DEFAULTS.

The shared [hal] table supplies the vault path and the local model settings.
"""

import os
import tomllib
from pathlib import Path

SECTION = "web"
DEFAULTS: dict = {
    "home": "London",
    "country": "GB",  # place names prefer this country (ISO code)
    "feeds": {
        "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
        "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "Hacker News": "https://hnrss.org/frontpage",
        "The Guardian UK": "https://www.theguardian.com/uk/rss",
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
