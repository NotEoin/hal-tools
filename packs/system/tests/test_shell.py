"""Tests for `shell_look`'s argv allowlist, path rule and the capped runner (REQ-PACK-20 to 22)."""

import os
import shutil
import signal
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from halshell import pathrule, readonly, run, tools

PROBES = Path(__file__).parent / "data" / "shell_probes.txt"


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A synthetic home directory with a file, a secret and a symlink to the secret."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in (
        "HAL_POLICY",
        "XDG_CONFIG_HOME",
        "XDG_STATE_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    ):
        monkeypatch.delenv(var, raising=False)
    policy = tmp_path / "policy.toml"
    policy.write_text('schema_version = 1\n[tools.shell_look]\nread_roots = ["~"]\n')
    policy.chmod(0o600)  # the loader refuses a policy file others can edit
    monkeypatch.setenv("HAL_POLICY", str(policy))
    (tmp_path / "notes.txt").write_text("alpha\nBeta\ngamma\n")
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "id_rsa").write_text("not a key")
    (tmp_path / "link").symlink_to(tmp_path / ".ssh" / "id_rsa")
    return tmp_path


def _probes() -> list[str]:
    return [ln for ln in PROBES.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


@pytest.mark.parametrize("command", _probes())
def test_shell_look_refuses_every_known_bypass(command, home):
    with pytest.raises(readonly.NotAllowed):
        readonly.check(command, path_ok=pathrule.read_ok, cwd=home)


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "ls -lhS notes.txt",
        "head -n 5 notes.txt",
        "head -n5 notes.txt",
        "cat -n notes.txt",
        "wc -l notes.txt",
        "du -sh --max-depth=1 .",
        "df -h",
        "uname -a",
        "uptime -p",
        "ps",
        "ps -u root -o pid,comm",
        "grep -rin alpha .",
        "grep -m 3 alpha notes.txt",
        "find . -maxdepth 2 -type f -name '*.txt'",
        "systemctl status ssh",
        "systemctl --user list-timers",
        "journalctl -u ssh -n 50 -p err --since '2026-10-01 10:00'",
        "ip -br addr",
        "ip addr show lo",
        "nmcli radio",
        "nmcli radio wifi",
        "nmcli -t -f NAME,TYPE connection show",
        "date +%Y-%m-%d",
        "tree -L 2 .",
        "stat notes.txt",
    ],
)
def test_shell_look_accepts_documented_examples(command, home):
    prog = command.split()[0]
    if not any((Path(d) / prog).is_file() for d in readonly.SYSTEM_DIRS):
        pytest.skip(f"{prog} is not installed here")
    argv = readonly.check(command, path_ok=pathrule.read_ok, cwd=home)
    assert argv[0].startswith(readonly.SYSTEM_DIRS)


def test_shell_look_confines_paths(home):
    for command in (
        "cat .ssh/id_rsa",
        "cat link",  # a symlink to a denied file
        "ls /etc",
        "ls ../../../../../../../..",
        f"cat {home}/.ssh/id_rsa",
        "ls /proc",
        "grep -r x /sys",
    ):
        with pytest.raises(readonly.NotAllowed):
            readonly.check(command, path_ok=pathrule.read_ok, cwd=home)


def test_shell_look_refuses_a_denied_cwd(home):
    with pytest.raises(readonly.NotAllowed):
        tools.look("ls", cwd=str(home / ".ssh"))


def test_shell_look_passes_the_checked_path_not_the_symlink(home):
    (home / "alias").symlink_to(home / "notes.txt")
    argv = readonly.check("cat alias", path_ok=pathrule.read_ok, cwd=home)
    assert argv[-1] == str((home / "notes.txt").resolve())


def test_shell_grammar_message_names_filter_and_head(home):
    with pytest.raises(readonly.NotAllowed, match="filter and head"):
        readonly.check("ls | head", path_ok=pathrule.read_ok, cwd=home)


def test_shell_look_filters_and_trims_output(home):
    res = tools.look("cat notes.txt", filter="A", head=2)
    assert res["output"].splitlines() == ["alpha", "Beta"]
    assert res["exit_code"] == 0
    assert res["argv"][0].endswith("/cat")


def test_shell_look_rejects_a_head_above_the_bound(home):
    with pytest.raises(ValueError):
        tools.look("ls", head=5000)


def test_programs_resolve_only_from_system_directories(home, monkeypatch, tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "ls").write_text("#!/bin/sh\necho owned\n")
    (fake / "ls").chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}:{os.environ.get('PATH', '')}")
    assert readonly.resolve_program("ls").startswith(readonly.SYSTEM_DIRS)


def test_shell_look_kills_process_group_on_timeout(tmp_path):
    pidfile = tmp_path / "child.pid"
    script = f"sleep 60 & echo $! > {pidfile}; wait"
    t0 = time.monotonic()
    res = run.capped(
        [shutil.which("sh") or "/bin/sh", "-c", script],
        timeout=1,
        cwd=str(tmp_path),
        env=run.minimal_env(),
        max_output=1000,
    )
    assert res["timed_out"] and res["exit_code"] == -9
    assert time.monotonic() - t0 < 10
    child = int(pidfile.read_text())
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(child, signal.SIG_DFL)


def test_shell_output_is_capped_without_buffering_all(tmp_path):
    t0 = time.monotonic()
    res = run.capped(
        ["/usr/bin/yes"],  # endless output; reading it all would never return
        timeout=20,
        cwd=str(tmp_path),
        env=run.minimal_env(),
        max_output=5000,
    )
    assert res["truncated"] and len(res["output"]) <= 5000
    assert time.monotonic() - t0 < 10


def test_runner_environment_hides_the_callers_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("HAL_TEST_SECRET", "hunter2")
    res = run.capped(
        ["/usr/bin/env"],
        timeout=5,
        cwd=str(tmp_path),
        env=run.minimal_env(),
        max_output=10000,
    )
    assert "hunter2" not in res["output"] and "HAL_TEST_SECRET" not in res["output"]


def test_shell_run_passes_shell_grammar_literally(home):
    res = tools.run("echo a | b ; c > d $HOME", cwd=str(home))
    assert res["output"].strip() == "a | b ; c > d $HOME"
    assert not (home / "d").exists()


def test_shell_run_timeout_is_capped(home, monkeypatch):
    seen = {}

    def fake(argv, *, timeout, **_):
        seen["timeout"] = timeout
        return {"exit_code": 0, "output": "", "errors": "", "truncated": False, "timed_out": False}

    monkeypatch.setattr(run, "capped", fake)
    tools.run("true", timeout=100000)
    assert seen["timeout"] == 600.0


def test_shell_run_refuses_an_empty_command(home):
    with pytest.raises(ValueError):
        tools.run("   ")


def test_shell_look_reads_only_the_roots_set_for_it_in_the_policy(home, monkeypatch):
    (home / "Documents").mkdir()
    (home / "Documents" / "a.txt").write_text("x")
    policy = home / "narrow.toml"
    policy.write_text('schema_version = 1\n[tools.shell_look]\nread_roots = ["~/Documents"]\n')
    policy.chmod(0o600)  # the loader refuses a policy file others can edit
    monkeypatch.setenv("HAL_POLICY", str(policy))
    assert pathrule.read_ok(home / "Documents" / "a.txt") is None
    assert pathrule.read_ok(home / "notes.txt") == "path:outside-roots"


def test_shell_look_refuses_a_hard_denied_path_inside_its_roots(home):
    assert pathrule.read_ok(home / ".ssh" / "id_rsa") == "path:hard-deny"
