"""Fires timers, alarms and Pomodoro changes as they come due.

python -m halclock.daemon
"""

from __future__ import annotations

import time
from datetime import datetime

from halkit.when import next_occurrence
from halnotify.alert import notify

from . import tools

POLL = 1  # seconds


def _next(at: float, rrule: str) -> float:
    """Epoch seconds of the occurrence of `rrule` after `at`, in local time."""
    return next_occurrence(datetime.fromtimestamp(at), rrule).timestamp()


def tick(now: float | None = None) -> int:
    """Fires the timers and alarms that are due and returns how many fired."""
    now = now or time.time()
    con = tools._db()
    fired = 0
    for r in con.execute("SELECT * FROM alarms WHERE fired IS NULL AND at <= ?", (now,)).fetchall():
        title = (
            f"Timer done: {r['label']}"
            if r["kind"] == "timer"
            else f"{r['label']} ({datetime.fromtimestamp(r['at']):%H:%M})"
        )
        notify(
            title,
            "Say 'Hal, snooze' for nine more minutes." if r["kind"] == "alarm" else "",
            urgent=True,
            speak=True,
        )
        if r["rrule"]:
            con.execute(
                "UPDATE alarms SET at = ? WHERE id = ?", (_next(r["at"], r["rrule"]), r["id"])
            )
        else:
            con.execute("UPDATE alarms SET fired = ? WHERE id = ?", (now, r["id"]))
        fired += 1
    p = con.execute("SELECT * FROM pomodoro WHERE k = 'p'").fetchone()
    if p and p["ends"] <= now:
        if p["phase"] == "work" and p["round"] < p["rounds"]:
            con.execute(
                "UPDATE pomodoro SET phase = 'rest', ends = ? WHERE k = 'p'",
                (now + p["rest"] * 60,),
            )
            notify(
                "Break time",
                f"Round {p['round']} of {p['rounds']} done: {p['rest']} minutes' rest.",
                speak=True,
            )
        elif p["phase"] == "rest":
            con.execute(
                "UPDATE pomodoro SET phase = 'work', round = round + 1, ends = ? WHERE k = 'p'",
                (now + p["work"] * 60,),
            )
            notify(
                "Back to work",
                f"Round {p['round'] + 1} of {p['rounds']}: {p['work']} minutes.",
                speak=True,
            )
        else:
            con.execute("DELETE FROM pomodoro")
            notify("Pomodoro finished", f"{p['rounds']} rounds done. Well worked.", speak=True)
        fired += 1
    con.commit()
    return fired


def main() -> None:
    """Runs the timer loop."""
    while True:
        tick()
        time.sleep(POLL)


if __name__ == "__main__":
    main()
