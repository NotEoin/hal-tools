"""hal-devices' tools: Bluetooth, USB, printers, monitors and cameras.

Every external command runs with a short timeout: bluetoothctl in particular
waits forever when there is no Bluetooth adapter. Printing uses CUPS (lp) and
needs confirmation through hal-hub.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _run(*cmd: str, timeout: float = 8) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _bt_ready() -> None:
    if not Path("/sys/class/bluetooth").exists() or not any(Path("/sys/class/bluetooth").iterdir()):
        raise RuntimeError("this computer has no Bluetooth adapter")


def bluetooth() -> dict:
    """Bluetooth on or off, and the paired devices with whether each is connected."""
    _bt_ready()
    powered = "Powered: yes" in _run("bluetoothctl", "show")
    devices = []
    for line in _run("bluetoothctl", "devices", "Paired").splitlines():
        m = re.match(r"Device (\S+) (.+)", line)
        if m:
            info = _run("bluetoothctl", "info", m.group(1))
            battery = re.search(r"Battery Percentage: \S+ \((\d+)\)", info)
            devices.append(
                {
                    "name": m.group(2),
                    "address": m.group(1),
                    "connected": "Connected: yes" in info,
                    "battery": int(battery.group(1)) if battery else None,
                }
            )
    return {"powered": powered, "devices": devices}


def _bt_device(name: str) -> str:
    for d in bluetooth()["devices"]:
        if name.lower() in d["name"].lower() or name.upper() == d["address"]:
            return d["address"]
    raise ValueError(f"no paired Bluetooth device matches {name!r}")


def bluetooth_connect(device: str) -> dict:
    addr = _bt_device(device)
    out = _run("bluetoothctl", "connect", addr, timeout=20)
    return {
        "device": device,
        "connected": "Connection successful" in out or "already connected" in out.lower(),
    }


def bluetooth_disconnect(device: str) -> dict:
    _run("bluetoothctl", "disconnect", _bt_device(device), timeout=15)
    return {"disconnected": device}


def bluetooth_power(on: bool = True) -> dict:
    _bt_ready()
    _run("bluetoothctl", "power", "on" if on else "off")
    return {"powered": bool(on)}


def usb() -> list[str]:
    """USB devices plugged in (hubs and root controllers left out)."""
    names = [re.sub(r"^Bus \d+ Device \d+: ID \S+ ", "", l) for l in _run("lsusb").splitlines()]
    return [n for n in names if not re.search(r"\bhub\b", n, re.I)]


def printers() -> dict:
    """Printers, the default one, and queued jobs."""
    out = _run("lpstat", "-p", "-d")
    names = re.findall(r"printer (\S+) is (\w+)", out)
    default = re.search(r"system default destination: (\S+)", out)
    jobs = _run("lpstat", "-o").strip().splitlines()
    return {
        "printers": [{"name": n, "state": s} for n, s in names],
        "default": default.group(1) if default else (names[0][0] if len(names) == 1 else None),
        "queue": jobs,
    }


def print_file(path: str, printer: str = "", copies: int = 1, double_sided: bool = False) -> dict:
    """Prints a file (PDF, image or text)."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"{path} is not a file")
    target = printer or printers()["default"]
    if not target:
        raise RuntimeError("no printer is set up")
    cmd = ["lp", "-d", target, "-n", str(int(copies))]
    if double_sided:
        cmd += ["-o", "sides=two-sided-long-edge"]
    done = subprocess.run([*cmd, str(p)], capture_output=True, text=True, timeout=60)
    if done.returncode:
        raise RuntimeError(done.stderr.strip())
    return {"printing": p.name, "printer": target, "job": done.stdout.strip()}


def monitors() -> list[dict]:
    """Connected displays with their connector and supported top resolution."""
    out = []
    for conn in sorted(Path("/sys/class/drm").glob("card*-*")):
        try:
            status = (conn / "status").read_text().strip()
        except OSError:
            continue
        if status != "connected":
            continue
        modes = (conn / "modes").read_text().split() if (conn / "modes").exists() else []
        out.append(
            {"connector": conn.name.split("-", 1)[1], "best_mode": modes[0] if modes else None}
        )
    return out


def cameras() -> list[dict]:
    """Video devices (webcams and capture cards)."""
    out = []
    for dev in sorted(Path("/sys/class/video4linux").glob("video*")):
        name = (dev / "name").read_text().strip() if (dev / "name").exists() else dev.name
        out.append({"device": f"/dev/{dev.name}", "name": name})
    return out
