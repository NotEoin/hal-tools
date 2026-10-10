"""hal-calendar's tools, as declared in hal-module.toml."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import ics, match, store, when
from .config import config_path, settings


def _now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def _label(d0: date, days: int, today: date) -> str:
    fmt = "%A %-d %B" if d0.year == today.year else "%A %-d %B %Y"
    return f"{d0:{fmt}}" + (f" + {days - 1} days" if days > 1 else "")


def _range(span: str) -> tuple[datetime, datetime, str]:
    """Turns 'today', 'tomorrow', 'this weekend', 'week', 'next 3 days', a weekday or a date such as
    '3 March 2031', 'the 3rd of March 2031' or '2031-03-03' into a time range."""
    now = _now()
    today = now.date()
    s = re.sub(r"[?.!]+$", "", (span or "today").strip().lower())
    s = re.sub(r"^(?:on|for|in|during|over)\s+", "", s)
    if s in ("today", "", "now"):
        d0, days = today, 1
    elif s == "tomorrow":
        d0, days = today + timedelta(days=1), 1
    elif s in ("week", "this week", "7 days", "the week", "next 7 days"):
        d0, days = today, 7
    elif s == "next week":
        d0, days = today + timedelta(days=7 - today.weekday()), 7
    elif s in ("weekend", "this weekend", "the weekend"):
        d0 = today + timedelta(days=(5 - today.weekday()) % 7 if today.weekday() < 6 else 0)    # Saturday, or today
        days = 2 if d0.weekday() == 5 else 1
    elif s in ("month", "this month", "30 days", "next 30 days"):
        d0, days = today, 30
    elif re.fullmatch(r"next \d+ days?", s):
        d0, days = today, int(s.split()[1])
    else:
        w = when.parse(s, now)
        if w.start is None:
            raise ValueError(f"cannot read the range {span!r}; say a day ('friday', '3 March 2031') "
                             "or a span ('this week', 'next 5 days')")
        d0, days = w.start.date(), 1
    start = datetime.combine(d0, time())
    return start, start + timedelta(days=days), _label(d0, days, today)


def add(title: str, when_text: str = "", duration_minutes: int = 0, location: str = "", notes: str = "",
        reminders: list[int] | None = None, repeat: str = "") -> dict:
    """Adds an event; the time may be in `when_text` or in the title itself."""
    w = when.parse(f"{when_text} {repeat}".strip() or title, _now(), default_time=None)
    if w.start is None and when_text:
        w = when.parse(f"{title} {when_text}", _now())
    if w.start is None:
        raise ValueError("no date or time found; say when, for example 'thursday at 10'")
    name = title if when_text else (w.rest or title)
    end = w.end or (w.start + timedelta(minutes=int(duration_minutes)) if duration_minutes else None)
    rem = [int(r) for r in reminders] if reminders else ([] if w.all_day else list(settings().get("default_reminders", [15])))
    e = store.save(store.Event(title=name.strip() or title, start=w.start, end=end, all_day=w.all_day,
                               rrule=w.rrule, location=location, notes=notes, reminders=rem))
    clash = [o for o in store.between(e.start, e.finish())
             if o["uid"] != e.uid and not o["all_day"] and not e.all_day]
    out = {"added": e.as_dict()}
    if clash:
        out["conflicts"] = [f"{o['title']} at {o['start'][11:16]}" for o in clash]
    return out


def agenda(span: str = "today") -> dict:
    """Lists the events in a day or range; says plainly when there are none."""
    start, end, label = _range(span)
    items = store.between(start, end)
    out = {"range": label, "events": [{"time": "all day" if o["all_day"] else o["start"][11:16] + "-" + o["end"][11:16],
                                       "date": o["start"][:10], "title": o["title"], "location": o["location"],
                                       "uid": o["uid"]} for o in items]}
    if not items:
        out["summary"] = f"Nothing on the calendar for {label}: that time is free."
    return out


def find(query: str, days: int = 365) -> list[dict]:
    """Returns upcoming (and the last month's) occurrences whose title, notes or location contain the
    words; failing that, the events the words most likely mean ('pottery class on friday')."""
    words = query.lower().split()
    now = _now()
    hits = store.between(now - timedelta(days=30), now + timedelta(days=int(days)))
    exact = [o for o in hits if all(w in f"{o['title']} {o['notes']} {o['location']}".lower() for w in words)]
    if exact:
        return exact[:20]
    ranked = match.rank(query, now, int(days))
    if not ranked:
        return []
    top = ranked[0][0]
    uids = {o["uid"] for s, o in ranked if s >= 0.5 and top - s < match.CLEAR_MARGIN}
    return [o for o in hits if o["uid"] in uids][:20]


def _resolve(event: str) -> store.Event:
    return match.resolve(event, _now())


def delete(event: str) -> dict:
    e = _resolve(event)
    store.delete(e.uid)
    return {"deleted": e.title, "was": e.start.isoformat(timespec="minutes"), "repeating": bool(e.rrule)}


def move(event: str, when_text: str) -> dict:
    e = _resolve(event)
    w = when.parse(when_text, _now(), default_time=e.start.time() if not e.all_day else None)
    if w.start is None:
        raise ValueError(f"cannot read {when_text!r}")
    length = e.finish() - e.start
    e.start = w.start
    e.end = w.end or (w.start + length if e.end else None)
    store.save(e)
    return {"moved": e.as_dict()}


def free(duration_minutes: int = 60, span: str = "week", day_start: int = 9, day_end: int = 18) -> list[str]:
    """Returns free slots at least `duration_minutes` long within working hours."""
    start, end, _ = _range(span)
    need = timedelta(minutes=int(duration_minutes))
    busy = [(datetime.fromisoformat(o["start"]), datetime.fromisoformat(o["end"]))
            for o in store.between(start, end) if not o["all_day"]]
    slots = []
    d = start.date()
    while datetime.combine(d, time()) < end:
        cursor = max(datetime.combine(d, time(int(day_start))), datetime.now())
        stop = datetime.combine(d, time(int(day_end)))
        for b0, b1 in sorted(busy):
            if b1 <= cursor or b0 >= stop:
                continue
            if b0 - cursor >= need:
                slots.append(f"{cursor:%a %-d %b %H:%M}-{b0:%H:%M}")
            cursor = max(cursor, b1)
        if stop - cursor >= need:
            slots.append(f"{cursor:%a %-d %b %H:%M}-{stop:%H:%M}")
        d += timedelta(days=1)
    return slots[:15]


def import_ics(path: str) -> dict:
    events = ics.parse(Path(path).expanduser().read_text(errors="ignore"))
    for e in events:
        store.save(e)
    return {"imported": len(events)}


def export_ics(path: str = "~/hal-calendar.ics") -> dict:
    p = Path(path).expanduser()
    events = store.all_events()
    p.write_text(ics.calendar(events))
    return {"exported": len(events), "path": str(p)}


def sync() -> dict:
    from .caldav import sync as run
    return run()


def calendars() -> list[dict]:
    from .caldav import client
    return client().calendars()


def setup_caldav(username: str, password: str, url: str = "https://caldav.icloud.com",
                 push_to: str = "") -> dict:
    """Stores CalDAV credentials (the password in a private file) and tests them."""
    pw = Path("~/.config/hal/caldav-password").expanduser()
    pw.parent.mkdir(parents=True, exist_ok=True)
    pw.write_text(password.strip())
    pw.chmod(0o600)
    cfg_path = config_path()
    text = cfg_path.read_text() if cfg_path.exists() else ""
    block = (f'\n[calendar.caldav]\nurl = "{url}"\nusername = "{username}"\n'
             f'password_file = "{pw}"\n' + (f'push_to = "{push_to}"\n' if push_to else ""))
    if "[calendar.caldav]" not in text:
        cfg_path.write_text(text.rstrip("\n") + "\n" + block)
    from .caldav import client
    return {"saved": True, "calendars": client().calendars()}
