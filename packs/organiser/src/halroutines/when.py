"""Understands dates, times, durations and repeats written in plain English.

    parse("dentist thursday at 10 for an hour")
    -> When(start=<Thu 10:00>, end=<Thu 11:00>, all_day=False, rrule=None, rest="dentist")

UK conventions: day before month in numeric dates, 24-hour or am/pm times.
A bare hour from 1 to 7 ("at 3") means the afternoon. Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_ABBR = {d[:3]: i for i, d in enumerate(WEEKDAYS)} | {
    "tues": 1,
    "thur": 3,
    "thurs": 3,
    "weds": 2,
}
MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
MONTH_ABBR = {m[:3]: i + 1 for i, m in enumerate(MONTHS)} | {"sept": 9}
NUMBERS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "forty-five": 45,
    "ninety": 90,
    "half an": 0.5,
    "a couple of": 2,
    "a few": 3,
}
PARTS = {
    "morning": time(9),
    "afternoon": time(14),
    "evening": time(18),
    "tonight": time(20),
    "night": time(21),
    "lunchtime": time(12, 30),
    "noon": time(12),
    "midday": time(12),
    "midnight": time(0),
}
UNITS = {
    "minute": 60,
    "min": 60,
    "mins": 60,
    "hour": 3600,
    "hr": 3600,
    "hrs": 3600,
    "day": 86400,
    "week": 604800,
    "fortnight": 1209600,
}
DAY_NAME = r"(?:mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)(?:day|nesday|rsday|urday|sday)?"
MONTH_NAME = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
NUM = r"(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|forty-five|ninety|half an|a couple of|a few)"


@dataclass
class When:
    start: datetime | None
    end: datetime | None = None
    all_day: bool = False
    rrule: str | None = None
    rest: str = ""


def _num(word: str) -> float:
    word = word.strip().lower()
    return float(word) if re.fullmatch(r"\d+(\.\d+)?", word) else float(NUMBERS.get(word, 1))


def _weekday(name: str) -> int:
    return DAY_ABBR[name.lower()[:3] if name.lower()[:4] not in DAY_ABBR else name.lower()[:4]]


class _Text:
    """The input, from which recognised phrases are cut as they are parsed."""

    def __init__(self, text: str) -> None:
        self.s = " " + re.sub(r"\s+", " ", text.strip()) + " "

    def take(self, pattern: str) -> re.Match | None:
        m = re.search(pattern, self.s, re.I)
        if m:
            self.s = self.s[: m.start()] + " " + self.s[m.end() :]
        return m

    @property
    def rest(self) -> str:
        out = re.sub(r"\s+", " ", self.s).strip(" ,.-")
        return re.sub(
            r"^(?:on|at|for|from|by|in)\s+|\s+(?:on|at|for|from|by|in)$", "", out, flags=re.I
        ).strip()


def _clock(m: re.Match, prefer_pm: bool = True) -> time:
    """Converts a matched time phrase to a time of day."""
    g = m.groupdict()
    if g.get("part"):
        return PARTS[g["part"].lower()]
    if g.get("rel"):
        hour = int(g["rh"]) % 12
        mins = {"quarter past": 15, "half past": 30, "quarter to": -15}[g["rel"].lower()]
        if prefer_pm and 1 <= hour <= 7:
            hour += 12
        base = datetime.combine(date.today(), time(hour)) + timedelta(minutes=mins)
        return base.time()
    hour, minute = int(g["h"]), int(g.get("m") or 0)
    ampm = (g.get("ap") or "").lower()
    if ampm.startswith("p") and hour < 12:
        hour += 12
    elif ampm.startswith("a") and hour == 12:
        hour = 0
    elif not ampm and not g.get("m") and prefer_pm and 1 <= hour <= 7:
        hour += 12
    return time(hour % 24, minute)


TIME = (
    r"(?:\b(?:at|@)\s*)?(?:(?P<rel>quarter past|half past|quarter to)\s+(?P<rh>\d{1,2})"
    r"|(?P<h>\d{1,2})(?:[:.](?P<m>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?)"
    r"|(?P<h2>\d{1,2})[:.](?P<m2>\d{2})"
    r"|\bat\s+(?P<h3>\d{1,2})\b"
    r"|\b(?P<part>noon|midday|midnight|lunchtime|tonight|morning|afternoon|evening|night)\b)"
)


def _find_time(t: _Text) -> time | None:
    m = t.take(TIME)
    if not m:
        return None
    g = m.groupdict()
    if g.get("h2"):
        return time(int(g["h2"]) % 24, int(g["m2"]))
    if g.get("h3"):
        h = int(g["h3"])
        return time(h + 12 if 1 <= h <= 7 else h % 24)
    return _clock(m)


def _find_date(t: _Text, now: datetime) -> tuple[date | None, bool]:
    """Returns (date, explicit): explicit is False when no date phrase was found."""
    today = now.date()
    if t.take(r"\bday after tomorrow\b"):
        return today + timedelta(days=2), True
    if t.take(r"\btomorrow\b|\btmrw\b"):
        return today + timedelta(days=1), True
    if t.take(r"\byesterday\b"):
        return today - timedelta(days=1), True
    if t.take(r"\btoday\b"):
        return today, True
    if re.search(r"\btonight\b", t.s, re.I):
        # Left in place so the time parser reads it as the evening.
        return today, True
    m = t.take(r"\b(\d{4})-(\d{2})-(\d{2})\b")
    if m:
        return date(int(m[1]), int(m[2]), int(m[3])), True
    m = t.take(
        rf"\b(?:on\s+)?(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_NAME})(?:\s+(\d{{4}}))?\b"
    )
    if not m:
        m2 = t.take(rf"\b({MONTH_NAME})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b")
        if m2:
            m = (None, m2[2], m2[1], m2[3])
    if m:
        day, month = (
            int(m[1]),
            MONTH_ABBR[m[2].lower()[:4] if m[2].lower()[:4] in MONTH_ABBR else m[2].lower()[:3]],
        )
        year = int(m[3]) if m[3] else today.year
        d = date(year, month, day)
        if not m[3] and d < today:
            d = date(year + 1, month, day)
        return d, True
    m = t.take(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
    if m:
        year = int(m[3]) if m[3] else today.year
        year += 2000 if year < 100 else 0
        d = date(year, int(m[2]), int(m[1]))
        if not m[3] and d < today:
            d = date(year + 1, int(m[2]), int(m[1]))
        return d, True
    m = t.take(r"\b(?:on\s+)?the\s+(\d{1,2})(?:st|nd|rd|th)\b")
    if m:
        day = int(m[1])
        d = date(today.year, today.month, day)
        if d < today:
            d = date(today.year + (today.month == 12), today.month % 12 + 1, day)
        return d, True
    m = t.take(rf"\b(next|this|on|coming)?\s*({DAY_NAME})\b")
    if m:
        target = _weekday(m[2])
        ahead = (target - today.weekday()) % 7
        if (m[1] or "").lower() == "next" and ahead == 0:
            ahead = 7
        elif (
            (m[1] or "").lower() == "next"
            and ahead < 7
            and today.weekday() < 5
            and target > today.weekday()
        ):
            # "next Thursday" said on a Monday means the Thursday after this one.
            ahead += 7
        return today + timedelta(days=ahead or 0), True
    m = t.take(r"\bnext week\b")
    if m:
        return today + timedelta(days=7 - today.weekday()), True
    return None, False


def _find_offset(t: _Text) -> timedelta | None:
    m = t.take(rf"\bin\s+{NUM}\s*(minute|min|mins|hour|hr|hrs|day|week|fortnight)s?\b")
    if m:
        return timedelta(seconds=_num(m[1]) * UNITS[m[2].lower()])
    if t.take(r"\bin half an hour\b"):
        return timedelta(minutes=30)
    return None


def _find_duration(t: _Text) -> timedelta | None:
    m = t.take(rf"\bfor\s+{NUM}\s*(minute|min|mins|hour|hr|hrs|day|week)s?\b")
    if m:
        return timedelta(seconds=_num(m[1]) * UNITS[m[2].lower()])
    if t.take(r"\bfor half an hour\b"):
        return timedelta(minutes=30)
    return None


def _find_until(t: _Text) -> time | None:
    m = t.take(r"\b(?:until|till|to|-)\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?\b")
    if not m:
        return None
    hour = int(m[1])
    if (m[3] or "").lower() == "pm" and hour < 12:
        hour += 12
    elif not m[3] and 1 <= hour <= 7:
        hour += 12
    return time(hour % 24, int(m[2] or 0))


def _find_repeat(t: _Text) -> str | None:
    m = t.take(r"\bevery\s+weekday\b|\bweekdays\b")
    if m:
        return "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    m = t.take(rf"\b(?:every|each)\s+((?:{DAY_NAME})(?:\s*(?:,|and)\s*(?:{DAY_NAME}))*)\b")
    if m:
        days = re.findall(DAY_NAME, m[1], re.I)
        codes = ",".join(["MO", "TU", "WE", "TH", "FR", "SA", "SU"][_weekday(d)] for d in days)
        return f"FREQ=WEEKLY;BYDAY={codes}"
    m = t.take(rf"\bevery\s+{NUM}?\s*(day|week|month|year)s?\b")
    if m:
        freq = {"day": "DAILY", "week": "WEEKLY", "month": "MONTHLY", "year": "YEARLY"}[
            m[2].lower()
        ]
        n = int(_num(m[1])) if m[1] else 1
        return f"FREQ={freq}" + (f";INTERVAL={n}" if n > 1 else "")
    m = t.take(r"\b(daily|weekly|fortnightly|monthly|yearly|annually)\b")
    if m:
        return {
            "daily": "FREQ=DAILY",
            "weekly": "FREQ=WEEKLY",
            "fortnightly": "FREQ=WEEKLY;INTERVAL=2",
            "monthly": "FREQ=MONTHLY",
            "yearly": "FREQ=YEARLY",
            "annually": "FREQ=YEARLY",
        }[m[1].lower()]
    return None


def parse(text: str, now: datetime | None = None, default_time: time | None = None) -> When:
    """Parses the date, time, length and repeat in `text`; `rest` is what is left.

    Args:
        text: For example "lunch with Sam next friday 1pm for 90 minutes".
        now: The reference time; the current time by default.
        default_time: Time to use when a date is given without one; None makes it all-day.
    """
    now = now or datetime.now().replace(second=0, microsecond=0)
    t = _Text(text)
    rrule = _find_repeat(t)
    offset = _find_offset(t)
    duration = _find_duration(t)
    if offset is not None:
        start = now + offset
        return When(start, start + duration if duration else None, False, rrule, t.rest)
    d, explicit = _find_date(t, now)
    clock = _find_time(t)
    until = _find_until(t) if clock else None
    if d is None and clock is None:
        if rrule:
            d = now.date()
        else:
            return When(None, rest=t.rest)
    if d is None:
        d = now.date()
        if datetime.combine(d, clock) < now and not rrule:
            d += timedelta(days=1)
    if clock is None:
        if default_time is None:
            return When(datetime.combine(d, time()), None, True, rrule, t.rest)
        clock = default_time
    start = datetime.combine(d, clock)
    if rrule and "BYDAY" in rrule and not explicit:
        codes = rrule.split("BYDAY=")[1].split(",")
        while ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][
            start.weekday()
        ] not in codes or start < now:
            start += timedelta(days=1)
    end = None
    if until is not None:
        end = datetime.combine(d, until)
        if end <= start:
            end += timedelta(days=1)
    elif duration:
        end = start + duration
    return When(start, end, False, rrule, t.rest)
