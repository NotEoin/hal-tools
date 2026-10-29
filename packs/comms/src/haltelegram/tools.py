"""hal-telegram's hal-hub tools. Stdlib only."""

from __future__ import annotations

from . import config


def status() -> dict:
    """Whether the bridge has a bot token and a paired chat (never the token itself)."""
    return {
        "token_saved": config.token_file().exists(),
        "paired": config.chat_file().exists(),
        "waiting_for_pairing": config.pairing_file().exists() and not config.chat_file().exists(),
    }
