"""Tests for scenes, schedules and the daemon, with tool calls captured instead of run."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RoutinesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")
        from halroutines import daemon, tools

        self.tools, self.daemon = tools, daemon
        self.calls = []
        self.args = []
        patcher = mock.patch.object(tools.hub_client, "call", side_effect=self._fake_call)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _fake_call(self, tool, args, caller, **kw):
        self.calls.append(tool)
        self.args.append((args, caller, kw))
        return "ok"

    def tearDown(self):
        self.tmp.cleanup()

    def test_scene_runs_every_step(self):
        out = self.tools.run_scene("Focus")
        self.assertEqual(len(out["steps"]), len(self.calls))
        self.assertIn("notify_dnd", self.calls)

    def test_routine_steps_go_through_policy(self):
        self.tools.run_scene("away")
        for args, caller, kw in self.args:
            self.assertEqual(caller, "routines")
            self.assertNotIn("_confirmed", args)
            self.assertIsNone(kw["routine"])

    def test_denied_step_is_skipped_and_the_rest_run(self):
        from halhub.client import ToolDenied

        def fake(tool, args, caller, **kw):
            self.calls.append(tool)
            if tool == "desktop_lock":
                raise ToolDenied("ask", "needs approval")
            return "ok"

        with mock.patch.object(self.tools.hub_client, "call", side_effect=fake):
            out = self.tools.run_scene("away")
        self.assertEqual([s["status"] for s in out["steps"]], ["ok", "ok", "skipped"])
        self.assertEqual(len(self.calls), 3)

    def test_failing_step_is_reported_as_an_error(self):
        from halhub.client import ToolFailed

        with mock.patch.object(
            self.tools.hub_client, "call", side_effect=ToolFailed("tool_error", "boom")
        ):
            out = self.tools.run_scene("away")
        self.assertEqual({s["status"] for s in out["steps"]}, {"error"})

    def test_saved_scene_validated(self):
        with self.assertRaises(ValueError):
            self.tools.save_scene("bad", [{"args": {}}])
        self.tools.save_scene("lamp", [{"tool": "rgb_colour", "args": {"colour": "blue"}}])
        self.tools.run_scene("lamp")
        self.assertEqual(self.calls, ["rgb_colour"])

    def test_schedule_runs_and_repeats(self):
        self.tools.schedule('{"tool": "rgb_off"}', "every day at 23:30", "lights out")
        at = self.tools._db().execute("SELECT at FROM schedules").fetchone()[0]

        class Quiet:
            def events(self):
                return []

        self.daemon.tick(Quiet(), at + 1)
        self.assertEqual(self.calls, ["rgb_off"])
        nxt = self.tools._db().execute("SELECT at FROM schedules").fetchone()[0]
        self.assertAlmostEqual(nxt - at, 86400)

    def test_unattended_run_uses_routine_caller(self):
        self.tools.run_routine("lights out", [{"tool": "rgb_off", "args": {}}])
        _, caller, kw = self.args[0]
        self.assertEqual(caller, "routines")
        self.assertEqual(kw["routine"].routine_id, "lights out")
        self.assertIn("rgb_off", kw["routine"].steps)
        self.assertTrue(kw["unattended"])

    def test_unattended_run_skips_ungranted_ask_steps_and_notifies(self):
        from halhub.client import ToolDenied

        def fake(tool, args, caller, **kw):
            self.calls.append(tool)
            if tool == "desktop_lock":
                raise ToolDenied("ask", "needs approval")
            return "ok"

        sent = []
        with (
            mock.patch.object(self.tools.hub_client, "call", side_effect=fake),
            mock.patch.object(self.tools, "notify", lambda *a, **k: sent.append(a)),
        ):
            out = self.tools.run_routine(
                "night", [{"tool": "routines_run", "args": {"name": "away"}}]
            )
        self.assertEqual([o["status"] for o in out], ["ok", "ok", "skipped"])
        self.assertEqual(len(sent), 1)
        self.assertIn("skipped desktop_lock", sent[0][1])
        self.assertIn("routines_run name=away", sent[0][1])

    def test_scene_step_in_a_routine_runs_under_the_scene_routine_id(self):
        self.tools.run_routine("night", [{"tool": "routines_run", "args": {"name": "away"}}])
        self.assertEqual({a[2]["routine"].routine_id for a in self.args}, {"away"})

    def test_save_scene_rejects_steps_that_are_not_tool_calls(self):
        for bad in ("not json", "[]", '[{"args": {}}]', '[{"tool": "x", "args": 3}]'):
            with self.assertRaises(ValueError, msg=bad):
                self.tools.save_scene("bad", bad)

    def test_schedule_needs_a_label(self):
        with self.assertRaises(ValueError):
            self.tools.schedule('{"tool": "rgb_off"}', "every day at 23:30", " ")

    def test_old_schedule_row_runs_its_target_tool(self):
        con = self.tools._db()
        con.execute(
            "INSERT INTO schedules (target, args, at, rrule, label) "
            "VALUES ('rgb_off', '{}', 1, '', 'old')"
        )
        con.commit()
        row = con.execute("SELECT * FROM schedules").fetchone()
        self.assertEqual(self.tools.stored_steps(row), [{"tool": "rgb_off", "args": {}}])

    def test_daemon_refuses_to_start_without_a_reachable_hub(self):
        from halhub.client import ToolFailed

        with mock.patch.object(
            self.daemon.hub_client, "call", side_effect=ToolFailed("unavailable", "no hub")
        ):
            with self.assertRaises(RuntimeError):
                self.daemon.check_hub()

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
