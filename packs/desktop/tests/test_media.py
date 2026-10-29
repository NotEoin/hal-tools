"""Tests for media tools that do not start or stop playback."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halmedia import tools  # noqa: E402


class MediaTest(unittest.TestCase):
    def test_status_lists_players(self):
        self.assertIsInstance(tools.status(), list)

    def test_bad_action_is_refused(self):
        with self.assertRaises(ValueError):
            tools.control("rewind-everything")

    def test_unknown_music_is_an_error(self):
        with self.assertRaises(ValueError):
            tools.play_music("zzqx no such artist zzqx")


if __name__ == "__main__":
    unittest.main()
