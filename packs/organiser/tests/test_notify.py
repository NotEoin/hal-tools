"""Tests for the notify tools and the daemon helper, with every channel stubbed out."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from halkit import notify as halkit_notify
from halnotify import alert, tools


class NotifyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        cfg = Path(self.tmp.name) / "c.toml"
        cfg.write_text(
            '[notify]\nntfy_topic = "test"\nquiet_from = 22\nquiet_until = 8\n'
            'channels = ["desktop", "phone"]\n'
        )
        env = mock.patch.dict(os.environ, {"HAL_STATE_DIR": self.tmp.name, "HAL_CONFIG": str(cfg)})
        env.start()
        self.addCleanup(env.stop)
        self.calls: list[object] = []
        for name in ("_desktop", "_speak"):
            fake = lambda *a, n=name: self.calls.append(n) or True  # noqa: E731 - test stub
            patcher = mock.patch.object(halkit_notify, name, fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        phone = lambda title, body, urgent, silent, url="": (  # noqa: E731 - test stub
            self.calls.append(("phone", silent)) or True
        )
        patcher = mock.patch.object(halkit_notify, "_ntfy", phone)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dnd_makes_phone_silent_but_urgent_breaks_through(self) -> None:
        tools.dnd(30)
        self.assertTrue(halkit_notify.quiet())
        out = tools.send("hi", "there", speak=True)
        self.assertTrue(out["quiet"])
        self.assertNotIn("_speak", self.calls)
        self.assertIn(("phone", True), self.calls)
        self.calls.clear()
        tools.send("fire", "now", urgent=True, speak=True)
        self.assertIn("_speak", self.calls)
        self.assertIn(("phone", False), self.calls)

    def test_sent_alerts_are_kept_in_the_history(self) -> None:
        tools.send("logged", "x")
        self.assertEqual(tools.history(1)[0]["title"], "logged")

    def test_unknown_channel_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            tools.send("x", channels=["telegram"])

    def test_daemon_helper_logs_and_returns_when_sending_fails(self) -> None:
        with mock.patch.object(halkit_notify, "send", side_effect=OSError("disk full")):
            with self.assertLogs("halnotify.alert", level="ERROR"):
                alert.notify("title")


if __name__ == "__main__":
    unittest.main()
