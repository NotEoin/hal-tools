"""Smoke tests for the desktop tools that change nothing."""

import sys
import unittest
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haldesk import tools


class DesktopTest(unittest.TestCase):
    @pytest.mark.host  # needs a desktop session
    def test_apps_are_listed(self):
        self.assertTrue(tools.apps())

    def test_unknown_app_and_missing_file_are_errors(self):
        with self.assertRaises(ValueError):
            tools.launch("no-such-application-xyz")
        with self.assertRaises(ValueError):
            tools.open_item(path="/no/such/file.txt")

    def test_open_needs_exactly_one_https_url_or_a_path(self):
        for kwargs in ({}, {"url": "https://a.example", "path": "/usr"}, {"url": "file:///etc"}):
            with self.assertRaises(ValueError):
                tools.open_item(**kwargs)

    def test_clipboard_set_pipes_the_text_to_wl_copy(self):
        with (
            mock.patch.object(tools.shutil, "which", return_value="/usr/bin/wl-copy"),
            mock.patch.object(tools.subprocess, "run") as run,
        ):
            self.assertEqual(tools.clipboard_set("hello"), {"copied": 5})
        self.assertEqual(run.call_args.args[0], ["wl-copy"])
        self.assertEqual(run.call_args.kwargs["input"], "hello")

    def test_clipboard_read_takes_no_text_argument(self):
        with self.assertRaises(TypeError):
            tools.clipboard("x")

    @pytest.mark.host  # needs a desktop session
    def test_reading_state_changes_nothing(self):
        self.assertIn(tools.theme()["mode"], ("dark", "light"))
        self.assertIsInstance(tools.volume()["muted"], bool)


if __name__ == "__main__":
    unittest.main()


def _fake_release(tmp_path, monkeypatch, text):
    release = tmp_path / "osrelease"
    release.write_text(text + "\n")
    monkeypatch.setenv("HAL_TOOLS_OSRELEASE", str(release))


def test_lock_refuses_under_wsl2_because_there_is_no_session(tmp_path, monkeypatch):
    _fake_release(tmp_path, monkeypatch, "5.15.153.1-microsoft-standard-WSL2")
    monkeypatch.setattr(tools, "_run", lambda *cmd: pytest.fail(f"ran {cmd}"))
    with pytest.raises(RuntimeError, match="Win\\+L"):
        tools.lock()


def test_volume_without_wpctl_under_wsl2_points_at_pulseaudio(tmp_path, monkeypatch):
    _fake_release(tmp_path, monkeypatch, "5.15.153.1-microsoft-standard-WSL2")
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="PulseAudio"):
        tools.volume()


def test_volume_without_wpctl_on_linux_says_to_install_wireplumber(tmp_path, monkeypatch):
    _fake_release(tmp_path, monkeypatch, "6.8.0-generic")
    monkeypatch.setattr(tools.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="wireplumber"):
        tools.volume()
