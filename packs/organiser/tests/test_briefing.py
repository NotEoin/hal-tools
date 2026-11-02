"""Tests that a briefing still forms when no other module answers."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halbrief import tools


class BriefingTest(unittest.TestCase):
    def _stub(self, fake) -> None:
        patch = mock.patch.object(tools, "_hub", fake)
        patch.start()
        self.addCleanup(patch.stop)

    def test_briefing_without_modules(self):
        self._stub(lambda *a, **k: None)
        text = tools.build("morning")
        self.assertTrue(text.startswith("Good "))

    def test_job_search_update(self):
        self._stub(
            lambda tool, **k: (
                "Good morning. Two applications are waiting." if tool == "jobs_digest" else None
            )
        )
        text = tools.build("jobs")
        self.assertTrue(text.endswith("Two applications are waiting."))
        self.assertEqual(text.count("Good "), 1)


class BriefCommandTest(unittest.TestCase):
    # regression: the timers ran `brief kind=...`, which the pack command line did not know
    def test_brief_command_delivers_the_named_kind(self):
        from halbrief import __main__ as cli

        with mock.patch.object(tools, "brief") as deliver:
            self.assertEqual(cli.brief(["kind=jobs"]), 0)
        deliver.assert_called_once_with("jobs")

    def test_brief_command_rejects_an_unknown_kind(self):
        from halbrief import __main__ as cli

        with mock.patch.object(tools, "brief") as deliver:
            self.assertEqual(cli.brief(["kind=lunch"]), 2)
        deliver.assert_not_called()

    def test_every_timer_starts_a_known_kind(self):
        from halbrief import __main__ as cli

        folder = Path(__file__).resolve().parents[1] / "src/halbrief/systemd"
        for timer in folder.glob("hal-briefing-*.timer"):
            kind = timer.read_text().split("hal-briefing@", 1)[1].split(".service", 1)[0]
            self.assertIn(kind, cli.KINDS, timer.name)


class TimerTest(unittest.TestCase):
    def test_morning_briefing_comes_after_quiet_hours(self):
        timer = (
            Path(__file__).resolve().parents[1] / "src/halbrief/systemd/hal-briefing-morning.timer"
        ).read_text()
        self.assertIn("OnCalendar=*-*-* 08:05", timer)


if __name__ == "__main__":
    unittest.main()
