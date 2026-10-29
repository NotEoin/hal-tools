"""Event storage in SQLite, and expansion of repeating events into occurrences.

Times are stored as local wall-clock ISO strings in the configured time zone,
so a weekly 9:00 meeting stays at 9:00 across clock changes. Repeats use a
subset of RFC 5545 RRULE: FREQ, INTERVAL, BYDAY (weekly), COUNT and UNTIL.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .config import data_dir

CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


@dataclass
class Event:
    title: str
    start: datetime
    end: datetime | None = None
    all_day: bool = False
    rrule: str | None = None
    location: str = ""
    notes: str = ""
    reminders: list[int] = field(default_factory=lambda: [15])  # minutes before
    uid: str = field(default_factory=lambda: f"{uuid.uuid4()}@hal")
    calendar: str = "local"
    href: str = ""
    etag: str = ""

    def finish(self) -> datetime:
        if self.end:
            return self.end
        return self.start + (timedelta(days=1) if self.all_day else timedelta(hours=1))

    def as_dict(self, occurrence: datetime | None = None) -> dict:
        start = occurrence or self.start
        end = start + (self.finish() - self.start)
        return {
            "uid": self.uid,
            "title": self.title,
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "all_day": self.all_day,
            "repeat": self.rrule,
            "location": self.location,
            "notes": self.notes,
            "reminders": self.reminders,
            "calendar": self.calendar,
        }


def db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "calendar.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS events (uid TEXT PRIMARY KEY, title TEXT, start TEXT, end TEXT, all_day INTEGER,
            rrule TEXT, location TEXT, notes TEXT, reminders TEXT, calendar TEXT, href TEXT, etag TEXT,
            updated TEXT, deleted INTEGER DEFAULT 0, dirty INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS reminded (uid TEXT, occurrence TEXT, minutes INTEGER,
            PRIMARY KEY (uid, occurrence, minutes));
    """)
    return con


def _row(r: sqlite3.Row) -> Event:
    return Event(
        title=r["title"],
        start=datetime.fromisoformat(r["start"]),
        end=datetime.fromisoformat(r["end"]) if r["end"] else None,
        all_day=bool(r["all_day"]),
        rrule=r["rrule"],
        location=r["location"] or "",
        notes=r["notes"] or "",
        reminders=[int(x) for x in (r["reminders"] or "").split(",") if x != ""],
        uid=r["uid"],
        calendar=r["calendar"],
        href=r["href"] or "",
        etag=r["etag"] or "",
    )


def save(e: Event, dirty: bool = True) -> Event:
    """Stores an event; `dirty` marks it for the next CalDAV push (pulled events are clean)."""
    con = db()
    con.execute(
        """INSERT OR REPLACE INTO events (uid, title, start, end, all_day, rrule, location, notes, reminders,
                   calendar, href, etag, updated, deleted, dirty) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)""",
        (
            e.uid,
            e.title,
            e.start.isoformat(),
            e.end.isoformat() if e.end else None,
            int(e.all_day),
            e.rrule,
            e.location,
            e.notes,
            ",".join(map(str, e.reminders)),
            e.calendar,
            e.href,
            e.etag,
            datetime.now().isoformat(timespec="seconds"),
            int(dirty),
        ),
    )
    con.commit()
    return e


def delete(uid: str) -> None:
    con = db()
    # Synced events are kept as tombstones until the deletion reaches the server.
    con.execute(
        "UPDATE events SET deleted = 1, updated = ? WHERE uid = ? AND href != ''",
        (datetime.now().isoformat(), uid),
    )
    con.execute("DELETE FROM events WHERE uid = ? AND (href IS NULL OR href = '')", (uid,))
    con.commit()


def dirty() -> list[Event]:
    """Returns events changed here since the last sync."""
    return [_row(r) for r in db().execute("SELECT * FROM events WHERE dirty = 1 AND deleted = 0")]


def get(uid: str) -> Event | None:
    r = db().execute("SELECT * FROM events WHERE uid = ? AND deleted = 0", (uid,)).fetchone()
    return _row(r) if r else None


def all_events(include_deleted: bool = False) -> list[Event]:
    sql = "SELECT * FROM events" + ("" if include_deleted else " WHERE deleted = 0")
    return [_row(r) for r in db().execute(sql)]


def _rule(rrule: str) -> dict:
    return dict(part.split("=", 1) for part in rrule.split(";") if "=" in part)


def _add_months(d: datetime, n: int) -> datetime | None:
    month = d.month - 1 + n
    year, month = d.year + month // 12, month % 12 + 1
    try:
        return d.replace(year=year, month=month)
    except ValueError:  # the 31st in a 30-day month has no occurrence
        return None


def occurrences(e: Event, start: datetime, end: datetime) -> list[datetime]:
    """Returns the event's start times that fall in [start, end), overlapping occurrences included."""
    length = e.finish() - e.start
    if not e.rrule:
        return [e.start] if e.start < end and e.start + length > start else []
    rule = _rule(e.rrule)
    freq, interval = rule.get("FREQ", "DAILY"), int(rule.get("INTERVAL", 1))
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    until = None
    if "UNTIL" in rule:
        u = rule["UNTIL"].rstrip("Z")
        until = (
            datetime.strptime(u[:15], "%Y%m%dT%H%M%S")
            if "T" in u
            else datetime.combine(datetime.strptime(u[:8], "%Y%m%d").date(), time(23, 59))
        )
    days = [CODES.index(c[-2:]) for c in rule.get("BYDAY", "").split(",") if c[-2:] in CODES]
    out, n, i = [], 0, 0
    while i < 5000:
        if freq == "WEEKLY" and days:
            week = e.start - timedelta(days=e.start.weekday()) + timedelta(weeks=i * interval)
            candidates = [week + timedelta(days=d) for d in sorted(days)]
        elif freq == "WEEKLY":
            candidates = [e.start + timedelta(weeks=i * interval)]
        elif freq == "DAILY":
            candidates = [e.start + timedelta(days=i * interval)]
        elif freq == "MONTHLY":
            candidates = [c for c in [_add_months(e.start, i * interval)] if c]
        else:
            candidates = [c for c in [_add_months(e.start, 12 * i * interval)] if c]
        i += 1
        for c in candidates:
            if c < e.start:
                continue
            if (until and c > until) or (count is not None and n >= count) or c >= end:
                return out
            n += 1
            if c + length > start:
                out.append(c)
    return out


def between(start: datetime, end: datetime) -> list[dict]:
    """Returns every occurrence of every event in [start, end), in time order."""
    found = []
    for e in all_events():
        for occ in occurrences(e, start, end):
            found.append(e.as_dict(occ))
    return sorted(found, key=lambda x: (x["start"], x["title"]))


def day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time())
    return start, start + timedelta(days=1)
