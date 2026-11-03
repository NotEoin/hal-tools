"""Tests for the `hal-comms` pack command line (`hal_comms.main`, a `halhub.pack` wrapper)."""

import tomllib
from pathlib import Path

import hal_comms
import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


@pytest.fixture(autouse=True)
def _empty_home(tmp_path, monkeypatch):
    """Keeps the run away from the real Hal config, policy and data."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HAL_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setenv("HAL_DATA", str(tmp_path / "data"))


def test_modules_match_the_hal_packs_entry_points():
    declared = tomllib.loads(PYPROJECT.read_text())["project"]["entry-points"]["hal.packs"]
    assert hal_comms.MODULES == declared


def test_tools_lists_the_packs_tools(capsys):
    assert hal_comms.main(["tools", "--json"]) == 0
    out = capsys.readouterr().out
    assert "mail_" in out


def test_cli_refuses_private_function_names(capsys):
    """REQ-PACK-24: the old `--stdin FUNCTION` path called any function by name."""
    assert hal_comms.main(["call", "_run"]) != 0
    assert hal_comms.main(["call", "mail__run"]) != 0
    assert hal_comms.main(["call", "--stdin", "_run"]) != 0
    assert "unknown_tool" in capsys.readouterr().err


def test_telegram_unit_starts_the_bridge(monkeypatch):
    """Regression: the unit ran `python -m haltelegram`, which printed usage and crash-looped."""
    import runpy

    import haltelegram.bridge

    unit = Path(__file__).resolve().parents[1] / "src/haltelegram/systemd/hal-telegram.service"
    lines = unit.read_text().splitlines()
    exec_start = next(line for line in lines if line.startswith("ExecStart="))
    _, flag, module, *args = exec_start.split()
    assert flag == "-m"
    started = []
    monkeypatch.setattr(haltelegram.bridge, "run", lambda: started.append(True) or 0)
    monkeypatch.setattr("sys.argv", [module, *args])
    with pytest.raises(SystemExit) as done:
        runpy.run_module(module, run_name="__main__", alter_sys=False)
    assert done.value.code == 0
    assert started == [True]
