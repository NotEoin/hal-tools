"""Manifest checks over every pack: schema v2 loads, flags match `tests/tool-policy.csv`, bounds exist.

Covers REQ-PACK-08 (tier and flags equal the policy table), REQ-PACK-09 (no `confirm`, no
default verdict, no `_` argument) and REQ-PACK-10 (numeric parameters are bounded). Packs whose
manifests are still schema 1 are skipped until their v2 step lands.
"""

import csv
import tomllib
from pathlib import Path

import pytest
from halhub.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[1]
FLAGS = ("network", "untrusted_output", "reviewable", "reversible", "runs_code")


def _manifests() -> list[Path]:
    found = sorted(ROOT.glob("packs/*/src/*/hal-module.toml"))
    return [p for p in found if tomllib.loads(p.read_text(encoding="utf-8")).get("schema") == 2]


def _policy() -> dict[str, dict[str, str]]:
    with (ROOT / "tests" / "tool-policy.csv").open(newline="", encoding="utf-8") as fh:
        return {row["tool"]: row for row in csv.DictReader(fh)}


MANIFESTS = _manifests()


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_manifest_loads_as_schema_v2(path):
    spec = load_manifest(path, source="path")
    assert spec.tools


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_manifests_match_policy_table(path):
    policy = _policy()
    for tool in load_manifest(path, source="path").tools:
        row = policy[tool.name]
        assert tool.tier == row["tier"], tool.name
        for flag in FLAGS:
            assert getattr(tool, flag) == (row[flag] == "true"), f"{tool.name}.{flag}"


def test_policy_table_names_only_tools_that_exist():
    names = {t.name for p in MANIFESTS for t in load_manifest(p, source="path").tools}
    assert set(_policy()) <= names


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_no_confirm_default_or_underscore_arguments(path):
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    for tool in data["tools"]:
        assert "confirm" not in tool and "default" not in tool, tool["name"]
        for name in tool.get("params", {}):
            assert not name.startswith("_") and name not in ("confirm", "confirmed"), tool["name"]


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_numeric_params_are_bounded(path):
    for tool in load_manifest(path, source="path").tools:
        for p in tool.params:
            if p.type in ("integer", "number"):
                assert p.minimum is not None and p.maximum is not None, f"{tool.name}.{p.name}"
