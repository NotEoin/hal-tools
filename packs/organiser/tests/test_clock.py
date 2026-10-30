"""Tests for durations and the daemon's firing, with notifications captured instead of sent."""

import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ClockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")
        from halclock import daemon, tools

        self.tools, self.daemon = tools, daemon
        self.sent = []
        daemon.notify = lambda title, body="", **kw: self.sent.append(title)

    def tearDown(self):
        self.tmp.cleanup()

    def test_durations(self):
        p = self.tools.parse_duration
        self.assertEqual(p("an hour and a half").total_seconds(), 5400)
        self.assertEqual(p("2:30").total_seconds(), 150)
        with self.assertRaises(ValueError):
            p("soon")

    def test_timer_fires_once(self):
        self.tools.timer("1 minute", "tea")
        self.assertEqual(self.daemon.tick(time.time() + 61), 1)
        self.assertEqual(self.daemon.tick(time.time() + 120), 0)
        self.assertEqual(self.sent, ["Timer done: tea"])

    def test_weekday_alarm_skips_the_weekend(self):
        friday_7am = datetime(2026, 10, 9, 7).timestamp()
        con = self.tools._db()
        con.execute(
            "INSERT INTO alarms (kind, label, at, rrule, created) VALUES ('alarm', 'Up', ?, ?, 0)",
            (friday_7am, "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"),
        )
        con.commit()
        self.daemon.tick(friday_7am + 1)
        nxt = self.tools._db().execute("SELECT at FROM alarms").fetchone()[0]
        self.assertEqual(datetime.fromtimestamp(nxt).strftime("%a %H:%M"), "Mon 07:00")

    def test_alarm_phrases(self):
        saturday = datetime(2026, 10, 10, 12, 0)
        real = self.tools._now
        self.tools._now = lambda: saturday
        try:
            cases = {
                "7 tomorrow morning": "Sun 11 Oct 07:00",
                "7am tomorrow": "Sun 11 Oct 07:00",
                "tomorrow at 7": "Sun 11 Oct 07:00",
                "6:30": "Sun 11 Oct 06:30",
                "in 20 minutes": "Sat 10 Oct 12:20",
                "at 7pm": "Sat 10 Oct 19:00",
                "8 this evening": "Sat 10 Oct 20:00",
                "every weekday at 7": "Mon 12 Oct 07:00",
            }
            for text, at in cases.items():
                self.assertEqual(self.tools.alarm(text)["at"], at, text)
        finally:
            self.tools._now = real

    def test_alarm_needs_a_time(self):
        with self.assertRaises(ValueError):
            self.tools.alarm("tomorrow")


if __name__ == "__main__":
    unittest.main()
