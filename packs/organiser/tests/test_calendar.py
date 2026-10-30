"""Tests for time parsing, repeats, ICS round trips and reminders, on a throwaway store."""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
FRIDAY = datetime(2026, 10, 9, 1, 50)


class CalendarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")

    def tearDown(self):
        self.tmp.cleanup()

    def test_parses_common_phrases(self):
        from halkit.when import parse

        cases = {
            "dentist thursday at 10": ("2026-10-15 10:00", "dentist"),
            "call mum tomorrow at 3": ("2026-10-10 15:00", "call mum"),
            "review tonight": ("2026-10-09 20:00", "review"),
            "meeting 10/11 at half past 2": ("2026-11-10 14:30", "meeting"),
            "tea in half an hour": ("2026-10-09 02:20", "tea"),
        }
        for text, (start, rest) in cases.items():
            w = parse(text, FRIDAY)
            self.assertEqual(w.start.strftime("%Y-%m-%d %H:%M"), start, text)
            self.assertEqual(w.rest, rest, text)

    def test_repeats_and_durations(self):
        from halkit.when import parse

        w = parse("gym every monday and wednesday at 7am for an hour", FRIDAY)
        self.assertEqual(w.rrule, "FREQ=WEEKLY;BYDAY=MO,WE")
        self.assertEqual((w.end - w.start).seconds, 3600)
        self.assertEqual(w.start.strftime("%a %H:%M"), "Mon 07:00")

    def test_weekly_occurrences(self):
        from halcal import store

        e = store.Event(
            "standup", datetime(2026, 10, 12, 9, 30), rrule="FREQ=WEEKLY;BYDAY=MO,WE;COUNT=3"
        )
        occ = store.occurrences(e, datetime(2026, 10, 1), datetime(2026, 12, 1))
        self.assertEqual([o.day for o in occ], [12, 14, 19])

    def test_ics_round_trip(self):
        from halcal import ics, store

        e = store.Event(
            "Dentist, check-up",
            datetime(2026, 10, 15, 10),
            location="Shoreditch",
            reminders=[10, 60],
        )
        back = ics.parse(ics.calendar([e]))[0]
        self.assertEqual(
            (back.title, back.start, back.location, sorted(back.reminders)),
            ("Dentist, check-up", e.start, "Shoreditch", [10, 60]),
        )

    def test_utc_times_become_local(self):
        from halcal import ics

        text = "BEGIN:VEVENT\nUID:x\nDTSTART:20260701T120000Z\nSUMMARY:Summer\nEND:VEVENT\n"
        self.assertEqual(ics.parse(text)[0].start.hour, 13)

    def test_reminder_fires_once(self):
        from halcal import reminders, store

        store.save(store.Event("Dentist", datetime(2026, 10, 15, 10), reminders=[15]))
        at = datetime(2026, 10, 15, 9, 46)
        self.assertEqual(len(reminders.due(at)), 1)
        con = store.db()
        con.execute(
            "INSERT INTO reminded VALUES (?, ?, ?)",
            (store.all_events()[0].uid, "2026-10-15T10:00", 15),
        )
        con.commit()
        self.assertEqual(reminders.due(at), [])


if __name__ == "__main__":
    unittest.main()
