"""Smoke tests for the desktop tools that change nothing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haldesk import tools  # noqa: E402


class DesktopTest(unittest.TestCase):
    def test_apps_are_listed(self):
        self.assertTrue(tools.apps())

    def test_unknown_app_and_missing_file_are_errors(self):
        with self.assertRaises(ValueError):
            tools.launch("no-such-application-xyz")
        with self.assertRaises(ValueError):
            tools.open_item("/no/such/file.txt")

    def test_reading_state_changes_nothing(self):
        self.assertIn(tools.theme()["mode"], ("dark", "light"))
        self.assertIsInstance(tools.volume()["muted"], bool)


if __name__ == "__main__":
    unittest.main()
