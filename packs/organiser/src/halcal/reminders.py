"""Reminder daemon: sends each event's reminders as phone push, desktop and spoken alerts.

Checks every 30 seconds. A reminder fires once, when its time arrives, and is
skipped if the daemon was down for more than MISSED_GRACE past it. All-day
events are announced at [calendar].all_day_reminder_hour on the day. When a
CalDAV account is set up, it also syncs every [calendar].sync_minutes.

    python -m halcal.reminders
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from halnotify.alert import notify

from . import store
from .settings import settings

log = logging.getLogger(__name__)

POLL = 30  # seconds
MISSED_GRACE = timedelta(minutes=20)


def due(now: datetime) -> list[tuple[dict, int, datetime]]:
    """Returns (occurrence, minutes before, fire time) for reminders due now and not yet sent."""
    cfg = settings()
    con = store.db()
    out = []
    for occ in store.between(now - timedelta(hours=1), now + timedelta(days=2)):
        start = datetime.fromisoformat(occ["start"])
        if occ["all_day"]:
            fires = [(-1, start.replace(hour=int(cfg.get("all_day_reminder_hour", 8))))]
        else:
            fires = [(m, start - timedelta(minutes=m)) for m in occ["reminders"]]
        for minutes, at in fires:
            if at <= now < at + MISSED_GRACE:
                sent = con.execute(
                    "SELECT 1 FROM reminded WHERE uid = ? AND occurrence = ? AND minutes = ?",
                    (occ["uid"], occ["start"], minutes),
                ).fetchone()
                if not sent:
                    out.append((occ, minutes, at))
    return out


def fire(now: datetime | None = None) -> int:
    """Sends every due reminder; returns how many were sent."""
    now = now or datetime.now()
    con = store.db()
    sent = 0
    for occ, minutes, _ in due(now):
        start = datetime.fromisoformat(occ["start"])
        if minutes == -1:
            title, body = (
                f"Today: {occ['title']}",
                "All day" + (f" at {occ['location']}" if occ["location"] else ""),
            )
        else:
            lead = (
                "now"
                if minutes == 0
                else f"in {minutes} minutes"
                if minutes < 60
                else f"in {minutes // 60} h {minutes % 60} min".replace(" 0 min", "")
            )
            title = f"{occ['title']} {lead}"
            body = f"{start:%H:%M}" + (f" at {occ['location']}" if occ["location"] else "")
        notify(title, body, urgent=minutes in (0, 5), speak=True)
        con.execute(
            "INSERT OR IGNORE INTO reminded VALUES (?, ?, ?)", (occ["uid"], occ["start"], minutes)
        )
        con.commit()
        sent += 1
    return sent


def main() -> None:
    last_sync = 0.0
    while True:
        fire()
        cfg = settings()
        if cfg.get("caldav", {}).get("url") and time.time() - last_sync > 60 * int(
            cfg.get("sync_minutes", 15)
        ):
            last_sync = time.time()
            try:
                from .caldav import sync

                sync()
            except Exception as e:  # noqa: BLE001 - a sync failure must not stop reminders
                log.warning("sync failed: %s", e)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
