"""Tests for quiet hours, do-not-disturb and history, with every channel stubbed out."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NotifyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        cfg = Path(self.tmp.name) / "c.toml"
        cfg.write_text(
            '[notify]\nntfy_topic = "test"\nquiet_from = 22\nquiet_until = 8\n'
            'channels = ["desktop", "phone"]\n'
        )
        os.environ["HAL_CONFIG"] = str(cfg)
        from halnotify import tools

        self.t = tools
        self.calls = []
        for name in ("_desktop", "_speak", "_telegram"):
            setattr(tools, name, lambda *a, n=name: self.calls.append(n) or True)
        tools._ntfy = lambda title, body, urgent, silent, url="": (
            self.calls.append(("phone", silent)) or True
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_dnd_makes_phone_silent_but_urgent_breaks_through(self):
        self.t.dnd(30)
        self.assertTrue(self.t.quiet())
        out = self.t.send("hi", "there", speak=True)
        self.assertTrue(out["quiet"])
        self.assertNotIn("_speak", self.calls)
        self.assertIn(("phone", True), self.calls)
        self.calls.clear()
        self.t.send("fire", "now", urgent=True, speak=True)
        self.assertIn("_speak", self.calls)
        self.assertIn(("phone", False), self.calls)

    def test_dnd_off_and_history(self):
        self.t.dnd(30)
        self.t.dnd(0)
        with mock.patch.object(self.t, "datetime") as dt:
            from datetime import datetime

            dt.now.return_value = datetime(2026, 10, 9, 12, 0)
            dt.fromisoformat = datetime.fromisoformat
            self.assertFalse(self.t.quiet())
        self.t.send("logged", "x")
        self.assertEqual(self.t.history(1)[0]["title"], "logged")


if __name__ == "__main__":
    unittest.main()
