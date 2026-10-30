"""Tests for scenes, schedules and the daemon, with tool calls captured instead of run."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RoutinesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
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

    def test_stored_desktop_open_and_clipboard_steps_are_upgraded(self):
        import json

        con = self.tools._db()
        steps = [
            {"tool": "desktop_open", "args": {"target": "https://a.example/x"}},
            {"tool": "desktop_open", "args": {"target": "~/notes.txt"}},
            {"tool": "notify_dnd", "args": {"minutes": 5}},
        ]
        con.execute("INSERT INTO scenes VALUES ('old', ?)", (json.dumps(steps),))
        con.execute(
            "INSERT INTO schedules (target, args, at, rrule, label) VALUES (?, ?, 0, '', 'x')",
            ("desktop_open", json.dumps({"target": "https://b.example"})),
        )
        con.execute(
            "INSERT INTO triggers (event, target, args) VALUES ('usb', 'desktop_clipboard', ?)",
            (json.dumps({"text": "hi"}),),
        )
        con.commit()
        con = self.tools._db()
        scene = json.loads(con.execute("SELECT steps FROM scenes WHERE name='old'").fetchone()[0])
        self.assertEqual(scene[0]["args"], {"url": "https://a.example/x"})
        self.assertEqual(scene[1]["args"], {"path": "~/notes.txt"})
        self.assertEqual(scene[2]["args"], {"minutes": 5})
        sched = con.execute("SELECT args FROM schedules").fetchone()[0]
        self.assertEqual(json.loads(sched), {"url": "https://b.example"})
        trig = con.execute("SELECT target FROM triggers").fetchone()[0]
        self.assertEqual(trig, "desktop_clipboard_set")
        self.assertEqual(self.tools.migrate(con), 0)


if __name__ == "__main__":
    unittest.main()
