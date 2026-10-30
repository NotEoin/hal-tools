"""Reminder daemon for tasks with a time: alerts when one falls due, and at 08:00 lists the day's
tasks.

python -m haltasks.reminders
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from . import tools
from .notify import notify
from .settings import data_dir, settings

POLL = 30  # seconds


def check(now: datetime | None = None) -> int:
    """Sends due reminders and the morning list; returns how many alerts went out."""
    now = now or datetime.now()
    lead = timedelta(minutes=int(settings()["remind_minutes"]))
    con = tools._db()
    sent = 0
    for r in con.execute(
        "SELECT * FROM tasks WHERE done IS NULL AND timed = 1 AND reminded = 0 AND due IS NOT NULL"
    ):
        due = datetime.fromisoformat(r["due"])
        if due - lead <= now < due + timedelta(hours=1):
            notify(f"Task due {due:%H:%M}: {r['title']}", r["notes"] or "", speak=True)
            con.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (r["id"],))
            sent += 1
    con.commit()
    marker = data_dir() / "morning"
    if now.hour >= 8 and (not marker.exists() or marker.read_text() != date.today().isoformat()):
        today = tools.list_tasks("today")["tasks"]
        if today:
            notify(
                f"{len(today)} task{'s' * (len(today) > 1)} today",
                "; ".join(t["title"] for t in today[:6]),
            )
            sent += 1
        marker.write_text(date.today().isoformat())
    return sent


def main() -> None:
    while True:
        tools.sync_from_vault()
        check()
        time.sleep(POLL)


if __name__ == "__main__":
    main()
