"""Golden checks for the unit files that ship with the modules (spec 08, "Units").

Every unit is listed in its module's manifest as `[[units]]`, uses only 06's placeholders, runs
from the pack environment, and carries no machine path.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from halhub.manifest import load_manifest

PACKS = Path(__file__).resolve().parents[1] / "packs"
MANIFESTS = sorted(PACKS.glob("*/src/*/hal-module.toml"))
PLACEHOLDERS = {"@ROOT@", "@HAL@", "@PYTHON@", "@BIN@", "@HOME@", "@STATE@"}
UNIT_SUFFIXES = {".service", ".timer"}
MACHINE_PATHS = ("/home/", "/Documents/", "hal-ecosystem", ".npm-global")
GPU_UNITS = {"hal-employment.service"}


def _units() -> list:
    return [
        pytest.param(unit, id=unit.file.name)
        for path in MANIFESTS
        for unit in load_manifest(path, source="path").units
    ]


def test_every_unit_file_is_listed_in_a_manifest() -> None:
    listed = {u.file.resolve() for p in MANIFESTS for u in load_manifest(p, source="path").units}
    shipped = {
        f.resolve()
        for p in MANIFESTS
        for f in (p.parent / "systemd").glob("*")
        if f.suffix in UNIT_SUFFIXES
    }
    assert shipped == listed
    assert not list(PACKS.glob("*/systemd")), "units live beside their manifest"


@pytest.mark.parametrize("unit", _units())
def test_unit_uses_only_supported_placeholders(unit) -> None:
    text = unit.file.read_text()
    assert set(re.findall(r"@[A-Z_]+@", text)) <= PLACEHOLDERS


@pytest.mark.parametrize("unit", _units())
def test_unit_has_no_machine_path_and_no_interpreter_guess(unit) -> None:
    text = unit.file.read_text()
    assert not [m for m in MACHINE_PATHS if m in text]
    for line in text.splitlines():
        if line.startswith("ExecStart=") and "python" in line:
            assert line.startswith("ExecStart=@PYTHON@ "), line


@pytest.mark.parametrize("unit", _units())
def test_only_the_employment_unit_is_gpu(unit) -> None:
    assert unit.gpu == (unit.file.name in GPU_UNITS)
    assert "X-HalGPU" not in unit.file.read_text()


def test_briefing_unit_no_longer_waits_for_the_voice_server() -> None:
    text = (PACKS / "organiser/src/halbrief/systemd/hal-briefing@.service").read_text()
    assert "hal-tts" not in text and "9880" not in text


def test_employment_unit_runs_the_launcher_that_reads_jobhunt_root_at_run_time() -> None:
    root = PACKS / "jobs/src/haljobs"
    text = (root / "systemd/hal-employment.service").read_text()
    assert "ExecStart=@ROOT@/bin/hal-employment-serve" in text
    launcher = (root / "bin/hal-employment-serve").read_text()
    assert "jobhunt_root" in launcher and (root / "bin/hal-employment-serve").stat().st_mode & 0o111


def test_employment_launcher_without_jobhunt_root_exits_naming_the_setting(tmp_path) -> None:
    # Regression: the launcher fell back to a default checkout path in the owner's home folder.
    config = tmp_path / "config.toml"
    config.write_text("[jobs]\n")
    launcher = PACKS / "jobs/src/haljobs/bin/hal-employment-serve"
    run = subprocess.run(
        [str(launcher)], env={"HAL_CONFIG": str(config), "PATH": os.environ["PATH"]},
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert run.returncode == 1 and "[jobs].jobhunt_root is not set" in run.stderr
