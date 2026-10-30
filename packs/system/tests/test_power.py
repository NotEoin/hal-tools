"""Tests for the power tools that change nothing."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halpower import tools


class PowerTest(unittest.TestCase):
    @pytest.mark.host  # reads the real systemd state
    def test_reading_state(self):
        self.assertIn("uptime", tools.uptime())
        self.assertIn("scheduled", tools.scheduled())

    def test_manifest_guards_every_session_ending_tool(self):
        import tomllib

        spec = tomllib.loads(
            (
                Path(__file__).resolve().parents[1] / "src" / "halpower" / "hal-module.toml"
            ).read_text()
        )
        guarded = {t["name"] for t in spec["tools"] if t.get("confirm")}
        self.assertEqual(guarded, {"power_suspend", "power_restart", "power_shutdown"})


if __name__ == "__main__":
    unittest.main()
