"""Reading and writing iCalendar (RFC 5545) events.

Reads VEVENTs with local, UTC, zoned and all-day times, durations, repeats and
alarms. Writes events in the configured time zone with its VTIMEZONE, which
CalDAV servers such as iCloud expect. Stdlib only (zoneinfo for time zones).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import settings
from .store import Event

# VTIMEZONE blocks for zones the writer knows; others fall back to UTC times.
VTIMEZONES = {
    "Europe/London": """BEGIN:VTIMEZONE
TZID:Europe/London
BEGIN:DAYLIGHT
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
TZNAME:BST
DTSTART:19700329T010000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
TZNAME:GMT
DTSTART:19701025T020000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE""",
}


def local_zone() -> ZoneInfo:
    return ZoneInfo(settings().get("timezone", "Europe/London"))


def _unfold(text: str) -> list[str]:
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _unescape(v: str) -> str:
    return v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _escape(v: str) -> str:
    return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _parse_time(params: str, value: str) -> tuple[datetime, bool]:
    """Returns (local naive datetime, all_day) from an iCalendar date or date-time."""
    if "VALUE=DATE" in params.upper() or re.fullmatch(r"\d{8}", value):
        return datetime.strptime(value[:8], "%Y%m%d"), True
    dt = datetime.strptime(value.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    tz = local_zone()
    if value.endswith("Z"):
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        m = re.search(r"TZID=([^;:]+)", params)
        if m:
            try:
                dt = dt.replace(tzinfo=ZoneInfo(m.group(1).strip('"')))
            except Exception:  # noqa: BLE001 - an unknown zone name is read as local time
                dt = dt.replace(tzinfo=tz)
        else:
            return dt, False
    return dt.astimezone(tz).replace(tzinfo=None), False


def _duration(v: str) -> timedelta:
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", v)
    if not m:
        return timedelta()
    sign = -1 if m[1] == "-" else 1
    w, d, h, mi, s = (int(x or 0) for x in m.groups()[1:])
    return sign * timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)


def parse(text: str, calendar: str = "local") -> list[Event]:
    """Returns the events in an iCalendar document."""
    events, cur, in_alarm = [], None, False
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {"reminders": []}
        elif line == "END:VEVENT" and cur is not None:
            if "start" in cur:
                end = cur.get("end") or (cur["start"] + cur["duration"] if "duration" in cur else None)
                events.append(Event(title=cur.get("title", "(untitled)"), start=cur["start"], end=end,
                                    all_day=cur.get("all_day", False), rrule=cur.get("rrule"),
                                    location=cur.get("location", ""), notes=cur.get("notes", ""),
                                    reminders=cur["reminders"] or [15], uid=cur.get("uid") or Event("", cur["start"]).uid,
                                    calendar=calendar))
            cur = None
        elif cur is None:
            continue
        elif line == "BEGIN:VALARM":
            in_alarm = True
        elif line == "END:VALARM":
            in_alarm = False
        else:
            name, _, value = line.partition(":")
            key, _, params = name.partition(";")
            key = key.upper()
            if in_alarm:
                if key == "TRIGGER" and not value.upper().startswith("VALUE"):
                    mins = int(-_duration(value).total_seconds() // 60)
                    if mins >= 0:
                        cur["reminders"].append(mins)
                continue
            if key == "SUMMARY":
                cur["title"] = _unescape(value)
            elif key == "DTSTART":
                cur["start"], cur["all_day"] = _parse_time(params, value)
            elif key == "DTEND":
                cur["end"], _ = _parse_time(params, value)
            elif key == "DURATION":
                cur["duration"] = _duration(value)
            elif key == "RRULE":
                cur["rrule"] = value
            elif key == "LOCATION":
                cur["location"] = _unescape(value)
            elif key == "DESCRIPTION":
                cur["notes"] = _unescape(value)
            elif key == "UID":
                cur["uid"] = value
    return events


def _fmt(dt: datetime, all_day: bool) -> str:
    return dt.strftime("%Y%m%d") if all_day else dt.strftime("%Y%m%dT%H%M%S")


def vevent(e: Event) -> str:
    """Returns one VEVENT block."""
    tzid = settings().get("timezone", "Europe/London")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if e.all_day:
        start = f"DTSTART;VALUE=DATE:{_fmt(e.start, True)}"
        end = f"DTEND;VALUE=DATE:{_fmt(e.finish(), True)}"
    elif tzid in VTIMEZONES:
        start = f"DTSTART;TZID={tzid}:{_fmt(e.start, False)}"
        end = f"DTEND;TZID={tzid}:{_fmt(e.finish(), False)}"
    else:
        utc = lambda d: d.replace(tzinfo=local_zone()).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
        start, end = f"DTSTART:{utc(e.start)}", f"DTEND:{utc(e.finish())}"
    lines = ["BEGIN:VEVENT", f"UID:{e.uid}", f"DTSTAMP:{stamp}", start, end, f"SUMMARY:{_escape(e.title)}"]
    if e.rrule:
        lines.append(f"RRULE:{e.rrule}")
    if e.location:
        lines.append(f"LOCATION:{_escape(e.location)}")
    if e.notes:
        lines.append(f"DESCRIPTION:{_escape(e.notes)}")
    for m in e.reminders:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_escape(e.title)}", f"TRIGGER:-PT{m}M", "END:VALARM"]
    lines.append("END:VEVENT")
    return "\r\n".join(lines)


def calendar(events: list[Event]) -> str:
    """Returns a complete VCALENDAR document holding the events."""
    tzid = settings().get("timezone", "Europe/London")
    parts = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Hal//hal-calendar//EN", "CALSCALE:GREGORIAN"]
    if tzid in VTIMEZONES and any(not e.all_day for e in events):
        parts.append(VTIMEZONES[tzid].replace("\n", "\r\n"))
    parts += [vevent(e) for e in events]
    parts.append("END:VCALENDAR")
    return "\r\n".join(parts) + "\r\n"


def today_local() -> date:
    return datetime.now(local_zone()).date()
