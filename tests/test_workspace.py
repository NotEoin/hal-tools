"""Tests for the workspace layout: the eight packs and the original module names."""

import importlib
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("organiser", "life", "comms", "online", "desktop", "system", "work", "jobs")


def load(path: Path) -> dict:
    return tomllib.loads(path.read_text())


def test_workspace_members_are_the_eight_packs():
    members = load(ROOT / "pyproject.toml")["tool"]["uv"]["workspace"]["members"]
    assert members == ["packs/*"]
    on_disk = sorted(p.name for p in (ROOT / "packs").iterdir() if (p / "pyproject.toml").exists())
    assert on_disk == sorted(PACKS)
    for pack in PACKS:
        assert load(ROOT / "packs" / pack / "pyproject.toml")["project"]["name"] == f"hal-{pack}"


def module_packages():
    for pack in PACKS:
        project = load(ROOT / "packs" / pack / "pyproject.toml")["project"]
        yield from project["entry-points"]["hal.packs"].values()


@pytest.mark.parametrize("package", sorted(module_packages()))
def test_every_module_imports_under_its_original_name(package):
    importlib.import_module(package)
    importlib.import_module(f"{package}.tools")


def test_every_module_ships_its_manifest_in_the_package():
    for package in module_packages():
        module = importlib.import_module(package)
        assert (Path(module.__file__).parent / "hal-module.toml").is_file(), package
