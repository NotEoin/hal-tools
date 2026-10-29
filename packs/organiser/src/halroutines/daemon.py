"""Runs schedules when they come due and triggers when their event happens.

python -m halroutines.daemon
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

from . import tools
from .config import settings

POLL = 15  # seconds


def _next(at: float, rrule: str) -> float:
    rule = dict(p.split("=") for p in rrule.split(";") if "=" in p)
    freq = rule.get("FREQ", "DAILY")
    n = int(rule.get("INTERVAL", 1))
    if "BYDAY" in rule:
        codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        days = {codes.index(c) for c in rule["BYDAY"].split(",")}
        step = 1
        while (datetime.fromtimestamp(at).weekday() + step) % 7 not in days:
            step += 1
        return at + step * 86400
    return at + {"DAILY": 86400, "WEEKLY": 604800}.get(freq, 86400) * n


def _idle_seconds() -> float:
    out = subprocess.run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.gnome.Mutter.IdleMonitor",
            "--object-path",
            "/org/gnome/Mutter/IdleMonitor/Core",
            "--method",
            "org.gnome.Mutter.IdleMonitor.GetIdletime",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout
    digits = "".join(c for c in out if c.isdigit())
    return int(digits) / 1000 if digits else 0


def _online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return True
    except OSError:
        return False


def _usb_devices() -> set[str]:
    return (
        {p.name for p in Path("/sys/bus/usb/devices").iterdir()}
        if Path("/sys/bus/usb/devices").exists()
        else set()
    )


def _disk_full() -> bool:
    total, used, _ = shutil.disk_usage("/")
    return used / total > 0.92


class Watcher:
    """Turns state changes into events, each reported once per change."""

    def __init__(self) -> None:
        self.online = _online()
        self.usb = _usb_devices()
        self.idle_fired = False
        self.disk_fired = False
        self.started = True

    def events(self) -> list[str]:
        found = ["login"] if self.started else []
        self.started = False
        on = _online()
        if on != self.online:
            found.append("online" if on else "offline")
            self.online = on
        usb = _usb_devices()
        if usb - self.usb:
            found.append("usb_added")
        self.usb = usb
        idle = _idle_seconds() >= 60 * int(settings()["idle_minutes"])
        if idle and not self.idle_fired:
            found.append("idle")
        self.idle_fired = idle
        full = _disk_full()
        if full and not self.disk_fired:
            found.append("disk_full")
        self.disk_fired = full
        return found


def tick(watcher: Watcher, now: float | None = None) -> list[str]:
    now = now or time.time()
    con = tools._db()
    ran = []
    for r in con.execute("SELECT * FROM schedules WHERE at <= ?", (now,)).fetchall():
        tools.run_target(r["target"], json.loads(r["args"]))
        ran.append(r["label"])
        if r["rrule"]:
            con.execute(
                "UPDATE schedules SET at = ? WHERE id = ?", (_next(r["at"], r["rrule"]), r["id"])
            )
        else:
            con.execute("DELETE FROM schedules WHERE id = ?", (r["id"],))
    con.commit()
    for event in watcher.events():
        for t in con.execute("SELECT * FROM triggers WHERE event = ?", (event,)).fetchall():
            tools.run_target(t["target"], json.loads(t["args"]))
            ran.append(f"{event}: {t['target']}")
    return ran


def main() -> None:
    w = Watcher()
    while True:
        for r in tick(w):
            print(f"{datetime.now():%H:%M:%S} ran {r}", flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
