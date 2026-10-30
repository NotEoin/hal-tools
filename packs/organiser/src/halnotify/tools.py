"""The notify module's tools: thin wrappers over `halkit.notify`, which owns delivery.

Channels are desktop, phone (ntfy) and voice (`[notify].say_command`). Quiet hours,
do-not-disturb and the history table live in `halkit.notify`, so every pack shares them.
"""

from __future__ import annotations

from halkit import notify as halkit_notify


def send(
    title: str,
    body: str = "",
    urgent: bool = False,
    speak: bool = False,
    channels: list[str] | None = None,
    url: str = "",
) -> dict:
    """Sends an alert; returns the channels it reached and whether quiet time held it back.

    Args:
        title: Short headline.
        body: Detail line.
        urgent: Breaks through quiet hours and do-not-disturb.
        speak: Also say it aloud (never during quiet time unless urgent).
        channels: Restrict to some of desktop, phone, voice; default the configured channels.
        url: Link opened when the phone notification is tapped.
    """
    return halkit_notify.send(
        title,
        body,
        urgent=urgent,
        speak=speak,
        channels=channels or None,
        url=url,
        source="notify_send",
    )


def dnd(minutes: int = halkit_notify.DEFAULT_DND_MINUTES) -> dict:
    """Turns do-not-disturb on for some minutes; 0 turns it off."""
    return halkit_notify.dnd(int(minutes))


def state() -> dict:
    """Returns whether notifications are quiet now, and until when."""
    return halkit_notify.state()


def history(limit: int = 20) -> list[dict]:
    """Returns the most recent alerts."""
    return halkit_notify.history(int(limit))
