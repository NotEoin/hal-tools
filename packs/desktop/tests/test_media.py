"""Tests for media tools that do not start or stop playback."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halmedia import tools


class MediaTest(unittest.TestCase):
    @pytest.mark.host  # needs PyGObject and a session bus
    def test_status_lists_players(self):
        self.assertIsInstance(tools.status(), list)

    def test_bad_action_is_refused(self):
        with self.assertRaises(ValueError):
            tools.control("rewind-everything")

    def test_unknown_music_is_an_error(self):
        with self.assertRaises(ValueError):
            tools.play_music("zzqx no such artist zzqx")

    def test_play_url_refuses_non_http_schemes_and_option_look_alikes(self):
        for url in ("file:///etc/passwd", "--input-file=/etc/passwd", "ftp://a.example/x"):
            with self.assertRaises(ValueError):
                tools.play_url(url)


if __name__ == "__main__":
    unittest.main()
