"""Tests for the interim `hal-work` command line (`hal_work.main`)."""

import tomllib
from pathlib import Path

import hal_work

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_modules_match_the_hal_packs_entry_points():
    declared = tomllib.loads(PYPROJECT.read_text())["project"]["entry-points"]["hal.packs"]
    assert hal_work.MODULES == declared


def test_no_arguments_lists_the_modules_and_fails(capsys):
    assert hal_work.main([]) == 2
    out = capsys.readouterr().out
    assert all(module in out for module in hal_work.MODULES)


def test_unknown_module_is_refused(capsys):
    assert hal_work.main(["no-such-module"]) == 2
    assert "no module" in capsys.readouterr().err


def test_a_module_without_a_tool_lists_its_tools(capsys):
    module = next(iter(hal_work.MODULES))
    assert hal_work.main([module]) == 0
    assert "list the tools" in capsys.readouterr().out
