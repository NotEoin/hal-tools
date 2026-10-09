"""Tests that a briefing still forms when no other module answers."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halbrief import tools  # noqa: E402


class BriefingTest(unittest.TestCase):
    def test_briefing_without_modules(self):
        tools._hub = lambda *a, **k: None
        text = tools.build("morning")
        self.assertTrue(text.startswith("Good "))


if __name__ == "__main__":
    unittest.main()
