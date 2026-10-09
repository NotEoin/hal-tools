"""hal-packages' tools: what needs updating, and what space can be reclaimed.

Reads apt, snap, flatpak and pip without root. Installing or upgrading uses
pkexec, which shows the desktop's own password prompt, and needs confirmation
through hal-hub. Clean-up only touches the user's own caches and trash.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


def _run(*cmd: str, timeout: float = 120) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def updates() -> dict:
    """Updates waiting for apt, snap and flatpak packages."""
    apt = list(dict.fromkeys(l.split("/")[0] for l in _run("apt", "list", "--upgradable").splitlines()[1:] if "/" in l))
    snaps = [l.split()[0] for l in _run("snap", "refresh", "--list").splitlines()[1:] if l.strip()] \
        if shutil.which("snap") else []
    flat = [l.split("\t")[0] for l in _run("flatpak", "remote-ls", "--updates", "--columns=application").splitlines()
            if l.strip()] if shutil.which("flatpak") else []
    security = list(dict.fromkeys(l.split("/")[0] for l in _run("apt", "list", "--upgradable").splitlines()
                                  if "-security" in l))
    return {"apt": len(apt), "apt_security": security[:20], "apt_packages": apt[:40], "snap": snaps, "flatpak": flat,
            "reboot_required": Path("/var/run/reboot-required").exists()}


def upgrade() -> dict:
    """Installs every apt update (asks for the password through the desktop)."""
    done = subprocess.run(["pkexec", "bash", "-c", "apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade"],
                          capture_output=True, text=True, timeout=3600)
    if done.returncode:
        raise RuntimeError(done.stderr.strip()[-400:] or "the upgrade was cancelled")
    return {"upgraded": True, "summary": done.stdout.strip().splitlines()[-3:]}


def install(package: str) -> dict:
    """Installs an apt package by exact name (asks for the password through the desktop)."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9.+-]+", package):
        raise ValueError(f"not a package name: {package!r}")
    done = subprocess.run(["pkexec", "apt-get", "install", "-y", package], capture_output=True, text=True, timeout=1800)
    if done.returncode:
        raise RuntimeError(done.stderr.strip()[-400:] or "the install was cancelled")
    return {"installed": package}


def search(query: str, limit: int = 15) -> list[dict]:
    """Searches the apt package lists."""
    out = []
    for line in _run("apt-cache", "search", "--names-only", query).splitlines()[:int(limit)]:
        name, _, desc = line.partition(" - ")
        out.append({"package": name, "description": desc})
    return out


def is_installed(name: str) -> dict:
    status = _run("dpkg-query", "-W", "-f=${Status} ${Version}", name)
    snap = name in _run("snap", "list") if shutil.which("snap") else False
    return {"package": name, "apt": "install ok installed" in status, "version": status.split()[-1] if status else None,
            "snap": snap, "command": shutil.which(name)}


def _size(path: Path) -> int:
    out = _run("du", "-sb", str(path), timeout=300)
    return int(out.split()[0]) if out else 0


def cleanup_report() -> dict:
    """Space that could be reclaimed: caches, trash, old logs, Docker and old snaps."""
    home = Path.home()
    items = {
        "user cache (~/.cache)": _size(home / ".cache"),
        "trash": _size(home / ".local/share/Trash"),
        "thumbnails": _size(home / ".cache/thumbnails"),
        "apt package cache": _size(Path("/var/cache/apt/archives")),
        "system journal": _size(Path("/var/log/journal")),
    }
    disabled = [l.split()[0] for l in _run("snap", "list", "--all").splitlines() if "disabled" in l]
    docker = _run("docker", "system", "df") if shutil.which("docker") else ""
    return {"sizes_gb": {k: round(v / 1e9, 2) for k, v in items.items()},
            "old_snap_revisions": disabled, "docker": docker.strip().splitlines()}


def cleanup(trash: bool = True, thumbnails: bool = True) -> dict:
    """Empties the trash and the thumbnail cache (the user's own files only)."""
    freed = 0
    targets = []
    if trash:
        targets += [Path.home() / ".local/share/Trash/files", Path.home() / ".local/share/Trash/info"]
    if thumbnails:
        targets.append(Path.home() / ".cache/thumbnails")
    for t in targets:
        if t.exists():
            freed += _size(t)
            shutil.rmtree(t)
            t.mkdir(parents=True)
    return {"freed_gb": round(freed / 1e9, 2)}
