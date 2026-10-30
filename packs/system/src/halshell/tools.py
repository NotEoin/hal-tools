"""hal-shell's tools: `shell_look` for read-only listings, `shell_run` as the explicit last resort.

`shell_look` never starts a shell: the command is split, checked against the program table in
`readonly.py` and run as an argv list by the capped runner. `shell_run` is `runs_code`, so it is
denied by default and the hub asks the user before every run. Output is cut to a readable size.
"""

from __future__ import annotations

import os
from pathlib import Path

from hal_system import proc

from . import readonly
from . import run as runner
from .pathrule import read_ok
from .settings import settings

MAX_HEAD = 2000  # lines, the upper bound of the `head` argument


def _exec(command: str, cwd: str, timeout: float) -> dict:
    done = proc.completed(
        ["bash", "-c", command], cwd=os.path.expanduser(cwd or "~"), timeout=timeout
    )
    limit = int(settings()["max_output"])
    out = done.stdout
    return {
        "exit_code": done.returncode,
        "output": out[:limit] + ("\n[cut]" if len(out) > limit else ""),
        "errors": done.stderr[-2000:],
    }


def look(command: str, cwd: str = "", filter: str = "", head: int = 0) -> dict:
    """Runs one read-only program from the table and returns its argv, output and exit code.

    `filter` keeps the lines that contain it (case-insensitive); `head` keeps the first lines.
    They replace pipes. Raises `NotAllowed` for anything not on the table.
    """
    base = Path(os.path.expanduser(cwd or "~")).resolve()
    if reason := read_ok(base):
        raise readonly.NotAllowed(f"cwd: {reason}")
    if not 0 <= head <= MAX_HEAD:
        raise ValueError(f"head must be between 0 and {MAX_HEAD}")
    argv = readonly.check(command, path_ok=read_ok, cwd=base)
    cfg = settings()
    extra = {}
    if "--user" in argv:  # the user manager is reached through the session bus
        for key in ("XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
            if key in os.environ:
                extra[key] = os.environ[key]
    res = runner.capped(
        argv,
        timeout=float(cfg["timeout_s"]),
        cwd=str(base),
        env=runner.minimal_env(extra),
        max_output=int(cfg["max_output"]),
    )
    lines = res["output"].splitlines()
    if filter:
        needle = filter.lower()
        lines = [ln for ln in lines if needle in ln.lower()]
    if head:
        lines = lines[:head]
    res["output"] = "\n".join(lines)
    return {"argv": argv, **res}


def run(command: str, cwd: str = "", timeout: int = 300) -> dict:
    """Runs any shell command. Confirmation is required through hal-hub."""
    return _exec(command, cwd, int(timeout))
