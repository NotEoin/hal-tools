"""Tests for repeat-rule stepping in the clock and routines daemons and in completing a task.

The daemons used private `_next` copies that ignored `INTERVAL` for daily and by-day rules and
stepped a monthly rule by one day. They now share `halkit.when.next_occurrence`.
"""

from datetime import datetime

import pytest
from halclock import daemon as clock
from halroutines import daemon as routines

SAT = datetime(2026, 10, 10, 9, 0)

CASES = {
    "FREQ=DAILY": "2026-10-11 09:00",
    "FREQ=DAILY;INTERVAL=2": "2026-10-12 09:00",  # the old clock copy stepped one day
    "FREQ=WEEKLY": "2026-10-17 09:00",
    "FREQ=WEEKLY;BYDAY=MO,FR": "2026-10-12 09:00",
    "FREQ=MONTHLY": "2026-11-10 09:00",  # the old daemon copies stepped one day
}


@pytest.mark.parametrize("rule", CASES)
@pytest.mark.parametrize("daemon", [clock, routines], ids=["clock", "routines"])
def test_daemon_steps_a_rule_to_the_next_calendar_occurrence(daemon, rule):
    got = datetime.fromtimestamp(daemon._next(SAT.timestamp(), rule))
    assert got.strftime("%Y-%m-%d %H:%M") == CASES[rule]
