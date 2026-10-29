"""Tests for scenes, schedules and the daemon, with tool calls captured instead of run."""
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RoutinesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")
        from halroutines import daemon, tools
        self.tools, self.daemon = tools, daemon
        self.calls = []
        tools.call_tool = lambda tool, args=None: self.calls.append(tool) or {"result": "ok"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_scene_runs_every_step(self):
        out = self.tools.run_scene("Focus")
        self.assertEqual(len(out["steps"]), len(self.calls))
        self.assertIn("notify_dnd", self.calls)

    def test_saved_scene_validated(self):
        with self.assertRaises(ValueError):
            self.tools.save_scene("bad", [{"args": {}}])
        self.tools.save_scene("lamp", [{"tool": "rgb_colour", "args": {"colour": "blue"}}])
        self.tools.run_scene("lamp")
        self.assertEqual(self.calls, ["rgb_colour"])

    def test_schedule_runs_and_repeats(self):
        self.tools.schedule("rgb_off", "every day at 23:30")
        at = self.tools._db().execute("SELECT at FROM schedules").fetchone()[0]

        class Quiet:
            def events(self):
                return []
        self.daemon.tick(Quiet(), at + 1)
        self.assertEqual(self.calls, ["rgb_off"])
        nxt = self.tools._db().execute("SELECT at FROM schedules").fetchone()[0]
        self.assertAlmostEqual(nxt - at, 86400)


if __name__ == "__main__":
    unittest.main()
