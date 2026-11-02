"""Tests for the power tools that change nothing."""

import subprocess
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

    def test_session_ending_tools_are_system_tier(self):
        import tomllib

        spec = tomllib.loads(
            (
                Path(__file__).resolve().parents[1] / "src" / "halpower" / "hal-module.toml"
            ).read_text()
        )
        guarded = {t["name"] for t in spec["tools"] if t.get("tier") == "system"}
        self.assertEqual(guarded, {"power_suspend", "power_restart", "power_shutdown"})


@pytest.fixture
def wsl2(tmp_path, monkeypatch):
    """Fakes a WSL2 kernel release."""
    release = tmp_path / "osrelease"
    release.write_text("5.15.153.1-microsoft-standard-WSL2\n")
    monkeypatch.setenv("HAL_TOOLS_OSRELEASE", str(release))


@pytest.mark.parametrize("call", [tools.suspend, tools.restart, tools.shutdown, tools.profile])
def test_power_tools_refuse_under_wsl2_without_running_anything(wsl2, monkeypatch, call):
    monkeypatch.setattr(tools, "_run", lambda *cmd: pytest.fail(f"ran {cmd}"))
    with pytest.raises(RuntimeError, match="WSL2"):
        call()


def test_suspend_runs_systemctl_on_plain_linux(tmp_path, monkeypatch):
    release = tmp_path / "osrelease"
    release.write_text("6.8.0-generic\n")
    monkeypatch.setenv("HAL_TOOLS_OSRELEASE", str(release))
    seen = []

    def fake_run(*cmd):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(tools, "_run", fake_run)
    assert tools.suspend() == {"suspending": True}
    assert seen == [("systemctl", "suspend")]


if __name__ == "__main__":
    unittest.main()
