"""hal-habits' tools: habits with daily targets and streaks, and a mood and sleep log.

A habit has a daily target ("water 8 glasses", "exercise 1"); logging adds to
today's count. Streaks count consecutive days that met the target. The nudge
daemon reminds you in the evening of habits not yet done.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from .settings import data_dir


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "habits.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS habits (name TEXT PRIMARY KEY, target REAL, unit TEXT, created
        TEXT);
        CREATE TABLE IF NOT EXISTS entries (habit TEXT, day TEXT, amount REAL, at TEXT);
        CREATE TABLE IF NOT EXISTS mood (day TEXT, at TEXT, score INTEGER, note TEXT);
        CREATE TABLE IF NOT EXISTS sleep (day TEXT PRIMARY KEY, hours REAL, quality INTEGER, note
        TEXT);
    """)
    return con


def _habit(con, name: str) -> sqlite3.Row:
    rows = con.execute("SELECT * FROM habits").fetchall()
    hit = next((r for r in rows if r["name"].lower() == name.lower()), None) or next(
        (r for r in rows if name.lower() in r["name"].lower()), None
    )
    if hit is None:
        raise ValueError(
            f"no habit {name!r}; have {', '.join(r['name'] for r in rows) or 'none yet'}"
        )
    return hit


def create(name: str, target: float = 1, unit: str = "times") -> dict:
    """Starts tracking a habit with a daily target, such as water 8 glasses."""
    con = _db()
    con.execute(
        "INSERT OR REPLACE INTO habits VALUES (?, ?, ?, ?)",
        (name, float(target), unit, date.today().isoformat()),
    )
    con.commit()
    return {"habit": name, "daily_target": f"{target:g} {unit}"}


def _done(con, name: str, day: str) -> float:
    return con.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM entries WHERE habit = ? AND day = ?", (name, day)
    ).fetchone()[0]


def _streak(con, h: sqlite3.Row) -> int:
    d, n = date.today(), 0
    if _done(con, h["name"], d.isoformat()) < h["target"]:
        d -= timedelta(days=1)
    while _done(con, h["name"], d.isoformat()) >= h["target"]:
        n += 1
        d -= timedelta(days=1)
    return n


def log(name: str, amount: float = 1, day: str = "") -> dict:
    """Records doing a habit (adds to today's count)."""
    con = _db()
    h = _habit(con, name)
    d = day or date.today().isoformat()
    con.execute(
        "INSERT INTO entries VALUES (?, ?, ?, ?)",
        (h["name"], d, float(amount), datetime.now().isoformat()),
    )
    con.commit()
    total = _done(con, h["name"], d)
    return {
        "habit": h["name"],
        "today": f"{total:g} of {h['target']:g} {h['unit']}",
        "done": total >= h["target"],
        "streak_days": _streak(con, h),
    }


def today() -> list[dict]:
    """Every habit's progress today and its streak."""
    con = _db()
    d = date.today().isoformat()
    return [
        {
            "habit": h["name"],
            "done": f"{_done(con, h['name'], d):g} of {h['target']:g} {h['unit']}",
            "complete": _done(con, h["name"], d) >= h["target"],
            "streak_days": _streak(con, h),
        }
        for h in con.execute("SELECT * FROM habits ORDER BY name")
    ]


def week() -> dict:
    """The last seven days: habits met per day, average mood and sleep."""
    con = _db()
    habits = con.execute("SELECT * FROM habits").fetchall()
    days = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        met = [h["name"] for h in habits if _done(con, h["name"], d) >= h["target"]]
        m = con.execute("SELECT AVG(score) FROM mood WHERE day = ?", (d,)).fetchone()[0]
        s = con.execute("SELECT hours FROM sleep WHERE day = ?", (d,)).fetchone()
        days.append(
            {
                "day": d,
                "habits_met": f"{len(met)} of {len(habits)}",
                "mood": round(m, 1) if m else None,
                "sleep_hours": s["hours"] if s else None,
            }
        )
    return {"days": days}


def mood(score: int, note: str = "") -> dict:
    """Logs mood from 1 (awful) to 5 (great), with an optional note."""
    s = int(score)
    if not 1 <= s <= 5:
        raise ValueError("mood is a number from 1 (awful) to 5 (great)")
    con = _db()
    con.execute(
        "INSERT INTO mood VALUES (?, ?, ?, ?)",
        (date.today().isoformat(), datetime.now().isoformat(), s, note),
    )
    con.commit()
    return {"mood": s, "noted": bool(note)}


def sleep(hours: float, quality: int = 0, note: str = "") -> dict:
    """Logs last night's sleep in hours, with quality from 1 to 5."""
    con = _db()
    con.execute(
        "INSERT OR REPLACE INTO sleep VALUES (?, ?, ?, ?)",
        (date.today().isoformat(), float(hours), int(quality) or None, note),
    )
    con.commit()
    avg = con.execute(
        "SELECT AVG(hours) FROM sleep WHERE day >= ?",
        ((date.today() - timedelta(days=7)).isoformat(),),
    ).fetchone()[0]
    return {"logged_hours": float(hours), "week_average": round(avg, 1)}


def remove(name: str) -> dict:
    con = _db()
    h = _habit(con, name)
    con.execute("DELETE FROM habits WHERE name = ?", (h["name"],))
    con.commit()
    return {"stopped_tracking": h["name"]}
