"""hal-jobs' tools: the job search, through jobhunt's command line and Hal Employment's API.

jobhunt lives in its own repository (configured as [jobs].jobhunt_root); this module
only calls it, so it holds no job data itself. Applications are still made in
Hal Employment, where every submit is pressed by the owner.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

from .config import settings


def _jobhunt(*args: str, timeout: float = 600) -> str:
    s = settings()
    root = Path(s.get("jobhunt_root") or s["jobhunt"]).expanduser()
    if not (root / "jobhunt").is_dir():
        raise RuntimeError(f"jobhunt not found at {root}; set [jobs].jobhunt_root")
    done = subprocess.run(["/usr/bin/python3", "-m", "jobhunt", *args], cwd=root, capture_output=True, text=True,
                          timeout=timeout)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout).strip()[-400:])
    return done.stdout.strip()


def _api(path: str) -> dict:
    url = settings()["employment_url"].rstrip("/") + "/api/" + path
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def queue() -> dict:
    """The jobs waiting to be applied for, best first."""
    try:
        data = _api("queue")
        return {"ready": len(data["jobs"]), "reserve": data["reserve"],
                "jobs": [{"company": j["company"], "title": j["title"], "score": j["score"], "location": j["location"]}
                         for j in data["jobs"]]}
    except OSError:
        return {"jobs": _jobhunt("queue").splitlines()}


def applications() -> list[dict]:
    """Applications in progress and sent, by stage."""
    try:
        return [{"company": j["company"], "title": j["title"], "status": j["status"]} for j in _api("applications")["jobs"]]
    except OSError:
        return [{"line": l} for l in _jobhunt("list", "-s", "all", "-n", "40").splitlines()]


def todo() -> str:
    """The job search to-do list: assessments, interviews, replies."""
    return _jobhunt("todo")


def check_email() -> str:
    """Syncs the job inbox now and reports what needs attention."""
    return _jobhunt("mail", "-q", timeout=900)


def digest() -> str:
    """A spoken-style summary of where the job search stands."""
    return _jobhunt("digest", "--spoken")


def status_counts() -> str:
    return _jobhunt("stats")


def open_employment() -> dict:
    """Opens Hal Employment in the browser."""
    subprocess.Popen(["gio", "open", settings()["employment_url"]], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return {"opened": settings()["employment_url"]}


def mark(job: str, status: str, note: str = "") -> str:
    """Records an application's progress: applied, assessment, interview, offer, rejected, withdrawn."""
    allowed = {"applied", "assessment", "interview", "offer", "rejected", "withdrawn", "skipped"}
    if status not in allowed:
        raise ValueError(f"status must be one of {', '.join(sorted(allowed))}")
    return _jobhunt("set", job, status, *([note] if note else []))
