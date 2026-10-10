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

    def test_job_search_update(self):
        tools._hub = lambda tool, **k: "Good morning. Two applications are waiting." if tool == "jobs_digest" else None
        text = tools.build("jobs")
        self.assertTrue(text.endswith("Two applications are waiting."))
        self.assertEqual(text.count("Good "), 1)


if __name__ == "__main__":
    unittest.main()
