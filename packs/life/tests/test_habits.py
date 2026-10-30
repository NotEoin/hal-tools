"""Tests for habit logging and streaks on a throwaway store."""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class HabitsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        from halhabits import tools

        self.t = tools

    def tearDown(self):
        self.tmp.cleanup()

    def test_target_and_streak(self):
        self.t.create("water", 2, "glasses")
        for i in (2, 1):
            self.t.log("water", 2, (date.today() - timedelta(days=i)).isoformat())
        out = self.t.log("water", 1)
        self.assertFalse(out["done"])
        self.assertEqual(out["streak_days"], 2)
        self.assertEqual(self.t.log("water", 1)["streak_days"], 3)

    def test_mood_range(self):
        with self.assertRaises(ValueError):
            self.t.mood(9)


if __name__ == "__main__":
    unittest.main()
