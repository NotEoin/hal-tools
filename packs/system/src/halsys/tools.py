"""hal-system's tools: what the computer is, what it is doing, and what went wrong.

Reads /proc and /sys directly and calls the standard tools (lscpu, lsblk,
nvidia-smi, sensors, systemctl, journalctl) when present. Stopping a process
or restarting a service needs confirmation through hal-hub.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import signal
import socket
import time
from pathlib import Path

from hal_system import proc


def _run(*cmd: str, timeout: float = 15) -> str:
    try:
        return proc.completed(cmd, timeout=timeout).stdout
    except (OSError, proc.ProcTimeout):
        return ""


def _gb(kb: float) -> float:
    return round(kb / 1024 / 1024, 1)


def _meminfo() -> dict:
    out = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, _, v = line.partition(":")
        out[k] = int(v.split()[0])
    return out


def _cpu_times() -> tuple[int, int]:
    parts = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    return sum(parts), parts[3] + parts[4]


def cpu() -> dict:
    """CPU model, cores, current use and load averages."""
    model = next(
        (
            ln.split(":", 1)[1].strip()
            for ln in Path("/proc/cpuinfo").read_text().splitlines()
            if ln.startswith("model name")
        ),
        platform.processor(),
    )
    t1, i1 = _cpu_times()
    time.sleep(0.4)
    t2, i2 = _cpu_times()
    use = 100 * (1 - (i2 - i1) / max(1, t2 - t1))
    load = os.getloadavg()
    freq = _run("bash", "-c", "grep MHz /proc/cpuinfo | awk '{s+=$4} END {print s/NR}'").strip()
    return {
        "model": model,
        "cores": os.cpu_count(),
        "use_percent": round(use, 1),
        "load_1_5_15": [round(x, 2) for x in load],
        "average_mhz": round(float(freq or 0)),
    }


def memory() -> dict:
    m = _meminfo()
    used = m["MemTotal"] - m["MemAvailable"]
    return {
        "total_gb": _gb(m["MemTotal"]),
        "used_gb": _gb(used),
        "available_gb": _gb(m["MemAvailable"]),
        "use_percent": round(100 * used / m["MemTotal"], 1),
        "swap_used_gb": _gb(m["SwapTotal"] - m["SwapFree"]),
        "swap_total_gb": _gb(m["SwapTotal"]),
    }


def disks() -> list[dict]:
    """Mounted filesystems with size and free space (real disks only)."""
    out = []
    for line in _run(
        "df",
        "-B1",
        "-x",
        "tmpfs",
        "-x",
        "devtmpfs",
        "-x",
        "squashfs",
        "-x",
        "overlay",
        "-x",
        "efivarfs",
        "--output=source,fstype,size,used,avail,pcent,target",
    ).splitlines()[1:]:
        p = line.split()
        if len(p) >= 7 and not p[6].startswith(("/snap", "/boot/efi")):
            out.append(
                {
                    "mount": " ".join(p[6:]),
                    "device": p[0],
                    "type": p[1],
                    "size_gb": round(int(p[2]) / 1e9, 1),
                    "used_gb": round(int(p[3]) / 1e9, 1),
                    "free_gb": round(int(p[4]) / 1e9, 1),
                    "use": p[5],
                }
            )
    return out


def gpu() -> list[dict]:
    """NVIDIA GPUs: use, memory, temperature, power, and the processes on them."""
    if not shutil.which("nvidia-smi"):
        return []
    rows = (
        _run(
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
            "--format=csv,noheader,nounits",
        )
        .strip()
        .splitlines()
    )
    procs = (
        _run(
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        )
        .strip()
        .splitlines()
    )
    out = []
    for r in rows:
        name, util, used, total, temp, power = [x.strip() for x in r.split(",")]
        out.append(
            {
                "name": name,
                "use_percent": int(util),
                "memory_used_mb": int(used),
                "memory_total_mb": int(total),
                "temperature_c": int(temp),
                "power_w": float(power) if power not in ("[N/A]", "") else None,
                "processes": [
                    {
                        "pid": int(p.split(",")[0]),
                        "name": p.split(",")[1].strip().rsplit("/", 1)[-1],
                        "memory_mb": int(p.split(",")[2]),
                    }
                    for p in procs
                    if p.strip()
                ],
            }
        )
    return out


def temperatures() -> dict:
    """Sensor readings in degrees C, from lm-sensors when installed, else /sys."""
    out: dict = {}
    raw = _run("sensors", "-j")
    if raw:
        try:
            for chip, feats in json.loads(raw).items():
                for feat, vals in feats.items():
                    if isinstance(vals, dict):
                        for k, v in vals.items():
                            if k.endswith("_input") and k.startswith("temp") and 0 < v < 150:
                                out[f"{chip.split('-')[0]} {feat}"] = round(v, 1)
        except json.JSONDecodeError:
            pass
    if not out:
        for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
            try:
                out[(zone / "type").read_text().strip()] = int((zone / "temp").read_text()) / 1000
            except (OSError, ValueError):
                continue
    for g in gpu():
        out[f"GPU {g['name']}"] = g["temperature_c"]
    return out


def battery() -> dict | None:
    for b in Path("/sys/class/power_supply").glob("BAT*"):

        def read(name: str, base: Path = b) -> str | None:
            return (base / name).read_text().strip() if (base / name).exists() else None

        return {"percent": int(read("capacity") or 0), "status": read("status")}
    return None


def overview() -> dict:
    """A one-call summary of the machine and its state now."""
    up = float(Path("/proc/uptime").read_text().split()[0])
    os_name = next(
        (
            ln.split("=", 1)[1].strip('"')
            for ln in Path("/etc/os-release").read_text().splitlines()
            if ln.startswith("PRETTY_NAME=")
        ),
        platform.system(),
    )
    board = Path("/sys/class/dmi/id/board_name")
    return {
        "host": socket.gethostname(),
        "os": os_name,
        "kernel": platform.release(),
        "motherboard": board.read_text().strip() if board.exists() else None,
        "uptime": f"{int(up // 86400)}d {int(up % 86400 // 3600)}h {int(up % 3600 // 60)}m",
        "cpu": cpu(),
        "memory": memory(),
        "gpu": gpu(),
        "disks": disks(),
        "battery": battery(),
    }


def processes(sort: str = "cpu", limit: int = 10, name: str = "") -> list[dict]:
    """Running processes, by CPU or memory use, optionally filtered by name."""
    key = "-%mem" if sort.startswith("mem") else "-%cpu"
    out = []
    for line in _run(
        "ps", "-eo", "pid,user,%cpu,%mem,rss,etime,comm,args", f"--sort={key}"
    ).splitlines()[1:]:
        p = line.split(None, 7)
        if len(p) < 8 or (name and name.lower() not in (p[6] + p[7]).lower()):
            continue
        out.append(
            {
                "pid": int(p[0]),
                "user": p[1],
                "cpu_percent": float(p[2]),
                "memory_percent": float(p[3]),
                "memory_mb": int(p[4]) // 1024,
                "running_for": p[5],
                "name": p[6],
                "command": p[7][:160],
            }
        )
        if len(out) >= int(limit):
            break
    return out


def _ancestors() -> set[int]:
    """Returns this process and its parents, which a kill must never reach."""
    pids, pid = set(), os.getpid()
    while pid > 1:
        pids.add(pid)
        try:
            pid = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return pids


def kill(process: str, force: bool = False) -> dict:
    """Stops processes by pid or program name (the user's own only, never a command-line match)."""
    me = os.environ.get("USER")
    if str(process).isdigit():
        targets = [int(process)]
    else:
        wanted = str(process).lower().removesuffix(".exe")
        targets = [
            p["pid"]
            for p in processes("cpu", 2000)
            if p["user"] == me and p["name"].lower() == wanted
        ]
    targets = [t for t in targets if t not in _ancestors()]
    if not targets:
        raise ValueError(f"no program of yours is called {process!r}")
    stopped = []
    for pid in targets:
        try:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
            stopped.append(pid)
        except (ProcessLookupError, PermissionError):
            continue
    return {"stopped": stopped}


def services(failed_only: bool = True) -> dict:
    """Systemd services: the failed ones (or all running user services)."""

    def units(*scope):
        state = ["--state=failed"] if failed_only else ["--state=running"]
        rows = _run(
            "systemctl", *scope, "list-units", "--type=service", *state, "--no-legend", "--plain"
        ).splitlines()
        return [r.split()[0] for r in rows if r.strip()]

    return {"system": units(), "user": units("--user")}


def service_status(name: str, user: bool = True) -> dict:
    scope = ["--user"] if user else []
    out = _run(
        "systemctl",
        *scope,
        "show",
        name,
        "--property=ActiveState,SubState,Description,ActiveEnterTimestamp",
    )
    info = dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)
    logs = _run("journalctl", *scope, "-u", name, "-n", "8", "--no-pager", "-o", "cat")
    return {**info, "recent_log": logs.strip().splitlines()[-8:]}


def service_restart(name: str, user: bool = True) -> dict:
    scope = ["--user"] if user else []
    cmd = (
        ["systemctl", *scope, "restart", name] if user else ["pkexec", "systemctl", "restart", name]
    )
    done = proc.completed(cmd, timeout=60)
    return {"restarted": done.returncode == 0, "error": done.stderr.strip()[:300]}


def logs(
    since: str = "1 hour ago", priority: str = "err", unit: str = "", limit: int = 30
) -> list[str]:
    """Recent system log lines at or above a priority (emerg, alert, crit, err, warning, info)."""
    cmd = [
        "journalctl",
        "--no-pager",
        "-o",
        "short-iso",
        "-p",
        priority,
        "--since",
        since,
        "-n",
        str(int(limit)),
    ]
    if unit:
        cmd += ["-u", unit]
    lines = _run(*cmd).strip().splitlines()
    user = (
        _run(
            "journalctl",
            "--user",
            "--no-pager",
            "-o",
            "short-iso",
            "-p",
            priority,
            "--since",
            since,
            "-n",
            str(int(limit)),
        )
        .strip()
        .splitlines()
    )
    merged = list(dict.fromkeys(ln for ln in lines + user if ln and not ln.startswith("-- ")))
    return sorted(merged)[-int(limit) :]


def hardware() -> dict:
    """CPU, memory slots, disks, graphics and other devices."""
    drives = []
    raw = _run("lsblk", "-d", "-J", "-o", "NAME,MODEL,SIZE,ROTA,TRAN")
    if raw:
        for d in json.loads(raw).get("blockdevices", []):
            if not d["name"].startswith(("loop", "zram")):
                drives.append(
                    {
                        "name": d["name"],
                        "model": (d.get("model") or "").strip(),
                        "size": d["size"],
                        "kind": "USB"
                        if d.get("tran") == "usb"
                        else "HDD"
                        if d.get("rota")
                        else "SSD",
                        "bus": d.get("tran"),
                    }
                )
    pci = _run("lspci")
    return {
        "cpu": cpu()["model"],
        "cores": os.cpu_count(),
        "memory_gb": memory()["total_gb"],
        "graphics": [
            ln.split(": ", 1)[1] for ln in pci.splitlines() if re.search(r"VGA|3D controller", ln)
        ],
        "audio": [ln.split(": ", 1)[1] for ln in pci.splitlines() if "Audio" in ln],
        "network": [
            ln.split(": ", 1)[1] for ln in pci.splitlines() if re.search(r"Ethernet|Network", ln)
        ],
        "drives": drives,
        "motherboard": Path("/sys/class/dmi/id/board_name").read_text().strip()
        if Path("/sys/class/dmi/id/board_name").exists()
        else None,
    }
