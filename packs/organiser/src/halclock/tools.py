"""hal-clock's tools: timers, alarms, a stopwatch and Pomodoro sessions.

Timers and alarms are rows in SQLite; the daemon (python -m halclock.daemon)
fires them through hal-notify, spoken and urgent, so they sound even in quiet
hours. Durations read like "9 minutes", "1h30" or "an hour and a half".
"""

from __future__ import annotations

import re
import sqlite3
import time
from datetime import datetime, timedelta

from . import when
from .settings import data_dir


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "clock.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS alarms (id INTEGER PRIMARY KEY, kind TEXT, label TEXT, at REAL,
            rrule TEXT, created REAL, fired REAL);
        CREATE TABLE IF NOT EXISTS stopwatch (k TEXT PRIMARY KEY, started REAL, elapsed REAL, laps TEXT);
        CREATE TABLE IF NOT EXISTS pomodoro (k TEXT PRIMARY KEY, work INTEGER, rest INTEGER, rounds INTEGER,
            round INTEGER, phase TEXT, ends REAL);
    """)
    return con


def parse_duration(text: str) -> timedelta:
    """Reads '9 minutes', '1h30', '90s', 'an hour and a half', '2:30' (minutes:seconds)."""
    t = text.lower().strip()
    m = re.fullmatch(r"(\d+):(\d{2})", t)
    if m:
        return timedelta(minutes=int(m[1]), seconds=int(m[2]))
    m = re.fullmatch(r"(\d+)h(\d+)", t.replace(" ", ""))
    if m:
        return timedelta(hours=int(m[1]), minutes=int(m[2]))
    t = t.replace("an hour and a half", "90 minutes").replace("half an hour", "30 minutes")
    t = re.sub(r"\b(an?|one)\b", "1", t).replace(" and a half", ".5").replace(" and ", " ")
    words = {
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "fifteen": 15,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "forty-five": 45,
        "sixty": 60,
    }
    for w, n in words.items():
        t = re.sub(rf"\b{w}\b", str(n), t)
    total = 0.0
    for num, unit in re.findall(
        r"(\d+(?:\.\d+)?)\s*(h|hr|hrs|hours?|m|min|mins|minutes?|s|sec|secs|seconds?)\b", t
    ):
        total += float(num) * (3600 if unit.startswith("h") else 1 if unit.startswith("s") else 60)
    if total == 0 and re.fullmatch(r"\d+(\.\d+)?", t):
        total = float(t) * 60
    if total <= 0:
        raise ValueError(f"cannot read the length {text!r}")
    return timedelta(seconds=total)


def _left(at: float) -> str:
    s = max(0, int(at - time.time()))
    return f"{s // 3600}h {s % 3600 // 60}m" if s >= 3600 else f"{s // 60}m {s % 60}s"


def timer(duration: str, label: str = "") -> dict:
    """Starts a countdown timer."""
    length = parse_duration(duration)
    at = time.time() + length.total_seconds()
    con = _db()
    cur = con.execute(
        "INSERT INTO alarms (kind, label, at, created) VALUES ('timer', ?, ?, ?)",
        (label or f"{duration} timer", at, time.time()),
    )
    con.commit()
    return {
        "id": cur.lastrowid,
        "label": label or f"{duration} timer",
        "ends": datetime.fromtimestamp(at).strftime("%H:%M:%S"),
    }


def _now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def alarm(when_text: str, label: str = "Alarm") -> dict:
    """Sets an alarm for a time ('7am', 'tomorrow at 6:30', '7 tomorrow morning', 'every weekday at 7').

    A bare hour is read as the morning ('at 7' is 07:00), as alarms mostly wake people up; say
    'pm' or 'evening' for later.
    """
    w = when.parse(when_text, _now(), default_time=None, prefer_pm=False)
    if w.start is None or w.all_day:
        raise ValueError(f"say a time for the alarm, for example '7am'; got {when_text!r}")
    con = _db()
    cur = con.execute(
        "INSERT INTO alarms (kind, label, at, rrule, created) VALUES ('alarm', ?, ?, ?, ?)",
        (label, w.start.timestamp(), w.rrule, time.time()),
    )
    con.commit()
    return {
        "id": cur.lastrowid,
        "label": label,
        "at": w.start.strftime("%a %-d %b %H:%M"),
        "repeat": w.rrule,
    }


def list_all() -> dict:
    con = _db()
    rows = con.execute("SELECT * FROM alarms WHERE fired IS NULL ORDER BY at").fetchall()
    out = {"timers": [], "alarms": []}
    for r in rows:
        item = {
            "id": r["id"],
            "label": r["label"],
            "at": datetime.fromtimestamp(r["at"]).strftime("%a %H:%M:%S"),
            "left": _left(r["at"]),
        }
        if r["rrule"]:
            item["repeat"] = r["rrule"]
        out["timers" if r["kind"] == "timer" else "alarms"].append(item)
    p = pomodoro("status")
    if p.get("phase"):
        out["pomodoro"] = p
    return out


def cancel(which: str = "") -> dict:
    """Cancels a timer or alarm by id or label words; 'all' cancels everything."""
    con = _db()
    rows = con.execute("SELECT * FROM alarms WHERE fired IS NULL").fetchall()
    if which.lower() in ("all", "everything"):
        hits = rows
    else:
        hits = [r for r in rows if str(r["id"]) == which or which.lower() in r["label"].lower()]
        if (
            not hits
            and len([r for r in rows if r["kind"] == "timer"]) == 1
            and which.lower() in ("", "timer", "the timer")
        ):
            hits = [r for r in rows if r["kind"] == "timer"]
    if not hits:
        raise ValueError(f"no timer or alarm matches {which!r}")
    for r in hits:
        con.execute("DELETE FROM alarms WHERE id = ?", (r["id"],))
    con.commit()
    return {"cancelled": [r["label"] for r in hits]}


def snooze(minutes: int = 9) -> dict:
    """Sets the most recently fired alarm again, some minutes from now."""
    con = _db()
    r = con.execute(
        "SELECT * FROM alarms WHERE fired IS NOT NULL ORDER BY fired DESC LIMIT 1"
    ).fetchone()
    if not r:
        raise ValueError("nothing has gone off to snooze")
    return timer(f"{int(minutes)} minutes", f"{r['label']} (snoozed)")


def stopwatch(action: str = "status") -> dict:
    """Starts, stops, laps, resets or reads the stopwatch."""
    con = _db()
    row = con.execute("SELECT * FROM stopwatch WHERE k = 'sw'").fetchone()
    started, elapsed, laps = (
        (row["started"], row["elapsed"], row["laps"]) if row else (None, 0.0, "")
    )
    now = time.time()
    current = elapsed + (now - started if started else 0)
    if action == "start" and not started:
        started = now
    elif action == "stop" and started:
        elapsed, started = current, None
    elif action == "lap":
        laps = f"{laps},{current:.1f}".strip(",")
    elif action == "reset":
        started, elapsed, laps, current = None, 0.0, "", 0.0
    con.execute("INSERT OR REPLACE INTO stopwatch VALUES ('sw', ?, ?, ?)", (started, elapsed, laps))
    con.commit()
    mins, secs = divmod(current, 60)
    return {
        "running": bool(started),
        "elapsed": f"{int(mins)}:{secs:04.1f}",
        "laps": [float(x) for x in laps.split(",") if x],
    }


def pomodoro(action: str = "start", work: int = 25, rest: int = 5, rounds: int = 4) -> dict:
    """Starts, stops or reads a Pomodoro session of work and rest periods."""
    con = _db()
    if action == "start":
        ends = time.time() + int(work) * 60
        con.execute(
            "INSERT OR REPLACE INTO pomodoro VALUES ('p', ?, ?, ?, 1, 'work', ?)",
            (int(work), int(rest), int(rounds), ends),
        )
        con.commit()
        return {
            "phase": "work",
            "round": 1,
            "of": int(rounds),
            "ends": datetime.fromtimestamp(ends).strftime("%H:%M"),
        }
    if action == "stop":
        con.execute("DELETE FROM pomodoro")
        con.commit()
        return {"stopped": True}
    r = con.execute("SELECT * FROM pomodoro WHERE k = 'p'").fetchone()
    if not r:
        return {"phase": None}
    return {"phase": r["phase"], "round": r["round"], "of": r["rounds"], "left": _left(r["ends"])}
