"""Tests for finding the event someone means, and for agenda ranges, on a throwaway store at a fixed time."""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SATURDAY = datetime(2026, 10, 10, 12, 0)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")
        from halcal import tools

        self.t = tools
        self._now = tools._now
        tools._now = lambda: SATURDAY

    def tearDown(self):
        self.t._now = self._now
        self.tmp.cleanup()

    def add(self, title, when_text):
        return self.t.add(title, when_text=when_text)["added"]


class MatchTest(Base):
    def test_delete_with_date_words(self):
        self.add("Pottery class", "friday at 6pm")
        self.add("Book club", "friday at 7pm")
        out = self.t.delete("pottery class on Friday")
        self.assertEqual(out["deleted"], "Pottery class")
        self.assertEqual([o["title"] for o in self.t.agenda("friday")["events"]], ["Book club"])

    def test_filler_and_extra_words(self):
        self.add("Haircut", "saturday at 10am")
        self.assertEqual(self.t.delete("my haircut appointment")["deleted"], "Haircut")
        self.add("Dentist check-up", "wednesday at 9am")
        self.assertEqual(
            self.t.delete("the dentist appointment on wednesday at 9am")["deleted"],
            "Dentist check-up",
        )

    def test_move_with_loose_words(self):
        self.add("Haircut", "saturday at 10am")
        moved = self.t.move("my haircut on saturday", "Sunday at 3pm")["moved"]
        self.assertEqual(moved["start"], "2026-10-11T15:00")
        self.assertEqual(len(self.t.find("haircut")), 1)

    def test_move_ignores_a_copy_already_at_the_new_time(self):
        self.add("Haircut", "sunday at 3pm")
        self.add("Haircut", "saturday at 10am")
        moved = self.t.move("my haircut", "Sunday at 3pm")["moved"]
        self.assertEqual(moved["start"], "2026-10-11T15:00")
        self.assertEqual(
            [o["start"] for o in self.t.find("haircut")], ["2026-10-11T15:00", "2026-10-11T15:00"]
        )

    def test_uid_is_exact(self):
        uid = self.add("Pottery class", "friday at 6pm")["uid"]
        self.assertEqual(self.t.delete(uid)["deleted"], "Pottery class")

    def test_named_day_picks_between_similar_events(self):
        self.add("Yoga class", "thursday at 6pm")
        self.add("Pottery class", "friday at 6pm")
        self.assertEqual(self.t.delete("the class on friday")["deleted"], "Pottery class")

    def test_ambiguous_words_list_the_candidates(self):
        self.add("Yoga class", "thursday at 6pm")
        self.add("Pottery class", "friday at 6pm")
        with self.assertRaises(ValueError) as err:
            self.t.delete("class")
        self.assertIn("Yoga class", str(err.exception))
        self.assertIn("Pottery class", str(err.exception))
        self.assertEqual(len(self.t.agenda("week")["events"]), 2)

    def test_no_match_is_an_error(self):
        self.add("Pottery class", "friday at 6pm")
        with self.assertRaises(ValueError):
            self.t.delete("dentist")

    def test_find_falls_back_to_fuzzy_words(self):
        self.add("Pottery class", "friday at 6pm")
        self.assertEqual(
            [o["title"] for o in self.t.find("pottery class on friday")], ["Pottery class"]
        )
        self.assertEqual(self.t.find("dentist"), [])

    def test_repeating_event_resolves_once(self):
        self.t.add("Gym", when_text="every monday at 7am")
        self.assertEqual(self.t.move("gym on monday", "monday at 8am")["moved"]["title"], "Gym")


class AgendaTest(Base):
    def test_single_dates(self):
        self.add("Dentist", "3 March 2031 at 10am")
        for span in (
            "3 March 2031",
            "2031-03-03",
            "the 3rd of March 2031",
            "on 3/3/2031",
            "March 3rd, 2031",
        ):
            got = self.t.agenda(span)
            self.assertEqual(got["range"], "Monday 3 March 2031", span)
            self.assertEqual([o["title"] for o in got["events"]], ["Dentist"], span)

    def test_empty_day_says_so(self):
        got = self.t.agenda("4 March 2031")
        self.assertEqual(got["events"], [])
        self.assertIn("Nothing", got["summary"])

    def test_spans(self):
        self.assertEqual(self.t.agenda("tomorrow")["range"], "Sunday 11 October")
        self.assertEqual(self.t.agenda("this weekend")["range"], "Saturday 10 October + 1 days")
        self.assertEqual(self.t.agenda("next 3 days")["range"], "Saturday 10 October + 2 days")
        self.assertEqual(self.t.agenda("friday")["range"], "Friday 16 October")
        with self.assertRaises(ValueError):
            self.t.agenda("whenever")


class ManifestTest(unittest.TestCase):
    def test_agenda_is_described_for_whats_on_questions(self):
        import tomllib

        spec = tomllib.loads(
            (Path(__file__).resolve().parents[1] / "src" / "halcal" / "hal-module.toml").read_text()
        )
        agenda = next(t for t in spec["tools"] if t["name"] == "calendar_agenda")
        text = (agenda["description"] + " " + agenda.get("keywords", "")).lower()
        for word in ("what's on", "anything", "free", "date"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
