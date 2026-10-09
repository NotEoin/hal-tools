"""hal-power's tools: suspend, restart and shut down, now or later, and power profiles.

Uses systemd (systemctl, loginctl, shutdown) and power-profiles-daemon. Every
action that ends the session needs confirmation through hal-hub.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _run(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def _ok(done: subprocess.CompletedProcess) -> None:
    if done.returncode:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip() or "the command failed")


def suspend() -> dict:
    _ok(_run("systemctl", "suspend"))
    return {"suspending": True}


def restart(minutes: int = 0) -> dict:
    """Restarts now, or in some minutes."""
    if int(minutes) > 0:
        _ok(_run("shutdown", "-r", f"+{int(minutes)}"))
        return {"restart_in_minutes": int(minutes)}
    _ok(_run("systemctl", "reboot"))
    return {"restarting": True}


def shutdown(minutes: int = 0) -> dict:
    """Shuts down now, or in some minutes."""
    if int(minutes) > 0:
        _ok(_run("shutdown", "-h", f"+{int(minutes)}"))
        return {"shutdown_in_minutes": int(minutes)}
    _ok(_run("systemctl", "poweroff"))
    return {"shutting_down": True}


def cancel_shutdown() -> dict:
    _run("shutdown", "-c")
    return {"cancelled": True}


def scheduled() -> dict:
    """Any restart or shutdown that is scheduled."""
    f = Path("/run/systemd/shutdown/scheduled")
    if not f.exists():
        return {"scheduled": None}
    info = dict(l.split("=", 1) for l in f.read_text().splitlines() if "=" in l)
    from datetime import datetime
    when = datetime.fromtimestamp(int(info.get("USEC", "0")) / 1e6)
    return {"scheduled": info.get("MODE"), "at": when.strftime("%a %H:%M")}


def profile(mode: str = "") -> dict:
    """Reads or sets the power profile: power-saver, balanced or performance."""
    if mode:
        _ok(_run("powerprofilesctl", "set", mode))
    return {"profile": _run("powerprofilesctl", "get").stdout.strip(),
            "available": re.findall(r"^\*?\s*(\S+):$", _run("powerprofilesctl", "list").stdout, re.M)}


def battery() -> dict:
    """Battery charge and state, where there is a battery."""
    for b in Path("/sys/class/power_supply").glob("BAT*"):
        r = lambda f: (b / f).read_text().strip() if (b / f).exists() else None  # noqa: E731
        return {"percent": int(r("capacity") or 0), "status": r("status"), "health": r("capacity_level")}
    return {"battery": "this computer runs on mains power"}


def uptime() -> dict:
    s = float(Path("/proc/uptime").read_text().split()[0])
    return {"uptime": f"{int(s // 86400)} days, {int(s % 86400 // 3600)} hours, {int(s % 3600 // 60)} minutes"}
