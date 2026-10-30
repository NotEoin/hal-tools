"""Never-raising alert helper for the organiser's long-running daemons.

A reminder daemon must survive a broken notification channel, so a failed send is logged and
swallowed here. Delivery itself is `halkit.notify.send`.
"""

import logging
import sqlite3

from halkit import notify as halkit_notify
from halkit.config import ConfigError

log = logging.getLogger(__name__)


def notify(title: str, body: str = "", urgent: bool = False, speak: bool = False) -> None:
    """Sends an alert through `halkit.notify`; logs and returns when it cannot be sent."""
    try:
        halkit_notify.send(title, body, urgent=urgent, speak=speak, source="organiser")
    except (OSError, sqlite3.Error, ConfigError):
        log.exception("notification %r not sent", title)
