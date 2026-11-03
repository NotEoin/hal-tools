"""Manifest checks over every pack: schema v2 loads, flags match the policy csv, bounds exist.

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


PATH_LIKE = ("path", "folder", "root", "file", "dir", "image", "repo")


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_path_params_declare_format_and_access(path):
    for tool in load_manifest(path, source="path").tools:
        for p in tool.params:
            is_path = p.format == "path"
            if any(p.name == w or p.name.endswith("_" + w) for w in PATH_LIKE):
                assert is_path, f"{tool.name}.{p.name} names a file but has no format = path"
            if is_path:
                assert p.access in ("read", "write"), f"{tool.name}.{p.name} has no access"


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.parent.name)
def test_exec_modules_run_on_their_packs_interpreter(path):
    # regression: desktop modules ran /usr/bin/python3, which cannot import the pack or hal-hub
    exec_argv = tomllib.loads(path.read_text())["module"].get("exec")
    if exec_argv and exec_argv[0].endswith("python3"):
        pytest.fail(f"{path}: exec runs {exec_argv[0]}, not the pack's {{python}}")


def test_desktop_pack_env_sees_the_system_pygobject():
    pyproject = tomllib.loads((ROOT / "packs/desktop/pyproject.toml").read_text())
    assert pyproject["tool"]["hal-pack"]["env"] == "system"


# modules whose tools talk TCP to a daemon on 127.0.0.1; a worker without network has its own
# loopback, so these must declare network (bubblewrap cannot open the host's loopback alone)
LOCAL_DAEMON_MODULES = {"rgb": "OpenRGB SDK server on 127.0.0.1:6742"}


@pytest.mark.parametrize("module", sorted(LOCAL_DAEMON_MODULES))
def test_tools_that_reach_a_local_daemon_declare_network(module):
    """Regression: every rgb tool failed with "SDK server is not running" under the sandbox."""
    path = next(p for p in MANIFESTS if p.parent.name == f"hal{module}")
    tools = load_manifest(path, source="path").tools
    assert all(t.network for t in tools), LOCAL_DAEMON_MODULES[module]
