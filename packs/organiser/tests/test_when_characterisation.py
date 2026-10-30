"""Characterisation tests: pin what the shared `when` parser and the routines fork do today.

These record current behaviour, right or wrong, so that replacing the copies with
`halkit.when` (steps H-17 and H-18) shows every difference. Where the fork differs from the
shared copy the case is listed twice, and the difference is deliberate to pin, not to keep.
The reference time is a fixed Saturday noon (2026-10-10 12:00).
"""

from datetime import datetime

import pytest
from halcal import when as shared
from halroutines import when as fork

NOW = datetime(2026, 10, 10, 12, 0)

# text -> (start, end time of day, all_day, rrule, rest); both parsers agree on these.
COMMON = {
    "tomorrow at 3pm": ("2026-10-11 15:00", None, False, None, ""),
    "every day at 23:00": ("2026-10-10 23:00", None, False, "FREQ=DAILY", ""),
    "every monday and friday at 9am": (
        "2026-10-12 09:00",
        None,
        False,
        "FREQ=WEEKLY;BYDAY=MO,FR",
        "",
    ),
    "in 20 minutes": ("2026-10-10 12:20", None, False, None, ""),
    "tonight": ("2026-10-10 20:00", None, False, None, ""),
    "next friday 1pm for 90 minutes": ("2026-10-16 13:00", "14:30", False, None, ""),
    "every weekday": (
        "2026-10-10 00:00",
        None,
        True,
        "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        "",
    ),
    "at 7": ("2026-10-10 19:00", None, False, None, ""),
    "every 2 weeks on tuesday": ("2026-10-13 00:00", None, True, "FREQ=WEEKLY;INTERVAL=2", ""),
    "today": ("2026-10-10 00:00", None, True, None, ""),
    "on 3 november": ("2026-11-03 00:00", None, True, None, ""),
    "quarter past 4": ("2026-10-10 16:15", None, False, None, ""),
    "lunchtime": ("2026-10-10 12:30", None, False, None, ""),
    "no time here": (None, None, False, None, "no time here"),
    "every month": ("2026-10-10 00:00", None, True, "FREQ=MONTHLY", ""),
    "half past 9 tomorrow": ("2026-10-11 09:30", None, False, None, ""),
    "noon": ("2026-10-10 12:00", None, False, None, ""),
    "in 2 hours for 30 minutes": ("2026-10-10 14:00", "14:30", False, None, ""),
}

# text -> (shared result, fork result): the cases where the two copies disagree.
DIFFERENT = {
    "at 6:30 in the morning": (
        ("2026-10-11 06:30", None, False, None, ""),
        ("2026-10-11 06:30", None, False, None, "the morning"),
    ),
    "friday 8-10pm": (
        ("2026-10-16 20:00", "22:00", False, None, ""),
        ("2026-10-16 22:00", None, False, None, "8"),
    ),
}


def summary(module, text: str) -> tuple:
    """Parses `text` against the fixed clock and flattens the result for comparison."""
    w = module.parse(text, NOW)
    return (
        w.start.strftime("%Y-%m-%d %H:%M") if w.start else None,
        w.end.strftime("%H:%M") if w.end else None,
        w.all_day,
        w.rrule,
        w.rest,
    )


@pytest.mark.parametrize("text", COMMON)
def test_shared_copy_parses_common_phrases_as_pinned(text):
    assert summary(shared, text) == COMMON[text]


@pytest.mark.parametrize("text", COMMON)
def test_routines_fork_agrees_on_common_phrases(text):
    assert summary(fork, text) == COMMON[text]


@pytest.mark.parametrize("text", DIFFERENT)
def test_shared_copy_keeps_its_pinned_result_where_the_fork_differs(text):
    assert summary(shared, text) == DIFFERENT[text][0]


@pytest.mark.parametrize("text", DIFFERENT)
def test_routines_fork_keeps_its_pinned_result_where_it_differs(text):
    assert summary(fork, text) == DIFFERENT[text][1]


def test_alarm_style_bare_hour_can_mean_morning():
    w = shared.parse("at 7", NOW, prefer_pm=False)
    assert w.start == datetime(2026, 10, 11, 7, 0)


def test_default_time_fills_a_date_given_without_a_time():
    w = shared.parse("tomorrow", NOW, default_time=datetime(2000, 1, 1, 9, 0).time())
    assert (w.start, w.all_day) == (datetime(2026, 10, 11, 9, 0), False)
