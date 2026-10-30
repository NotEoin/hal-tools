"""Tests for the `hal-online` pack command line (`hal_online.main`, a `halhub.pack` wrapper)."""

import tomllib
from pathlib import Path

import hal_online
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
    assert hal_online.MODULES == declared


def test_tools_lists_the_packs_tools(capsys):
    assert hal_online.main(["tools", "--json"]) == 0
    out = capsys.readouterr().out
    assert "web_" in out


def test_cli_refuses_private_function_names(capsys):
    """REQ-PACK-24: the old `--stdin FUNCTION` path called any function by name."""
    assert hal_online.main(["call", "_run"]) != 0
    assert hal_online.main(["call", "web__run"]) != 0
    assert hal_online.main(["call", "--stdin", "_run"]) != 0
    assert "unknown_tool" in capsys.readouterr().err
