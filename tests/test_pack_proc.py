"""Tests for the text-mode `proc.completed` helper that every pack carries."""

import importlib

import pytest

PACKS = ["comms", "desktop", "jobs", "organiser", "system", "work"]


@pytest.fixture(params=PACKS)
def proc(request):
    return importlib.import_module(f"hal_{request.param}.proc")


def test_output_comes_back_as_text(proc):
    done = proc.completed(["echo", "hi"], timeout=5)
    assert (done.returncode, done.stdout) == (0, "hi\n")


def test_nonzero_exit_is_reported_not_raised(proc):
    assert proc.completed(["false"], timeout=5).returncode == 1


def test_input_text_reaches_the_child(proc):
    assert proc.completed(["cat"], timeout=5, input="abc").stdout == "abc"


def test_a_hung_child_is_killed_at_the_timeout(proc):
    with pytest.raises(proc.ProcTimeout):
        proc.completed(["sleep", "30"], timeout=0.2)


def test_a_missing_program_raises_oserror(proc):
    with pytest.raises(OSError):
        proc.completed(["hal-no-such-program"], timeout=5)
