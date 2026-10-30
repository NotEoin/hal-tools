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

from .settings import settings

PACK_TIMEOUT = 1800  # seconds; drafting a pack runs the local model and searches the web


def _jobhunt(*args: str, timeout: float = 600) -> str:
    s = settings()
    root = Path(str(s["jobhunt_root"])).expanduser()
    if not (root / "jobhunt").is_dir():
        raise RuntimeError(f"jobhunt not found at {root}; set [jobs].jobhunt_root")
    done = subprocess.run(
        ["/usr/bin/python3", "-m", "jobhunt", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout).strip()[-400:])
    return done.stdout.strip()


def _api(path: str) -> dict:
    url = settings()["employment_url"].rstrip("/") + "/api/" + path
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 - the URL is the user-configured local Hal Employment server
        return json.loads(r.read())


def queue() -> dict:
    """The jobs waiting to be applied for, best first."""
    try:
        data = _api("queue")
        return {
            "ready": len(data["jobs"]),
            "reserve": data["reserve"],
            "jobs": [
                {
                    "company": j["company"],
                    "title": j["title"],
                    "score": j["score"],
                    "location": j["location"],
                }
                for j in data["jobs"]
            ],
        }
    except OSError:
        return {"jobs": _jobhunt("queue").splitlines()}


def applications() -> list[dict]:
    """Applications in progress and sent, by stage."""
    try:
        return [
            {"company": j["company"], "title": j["title"], "status": j["status"]}
            for j in _api("applications")["jobs"]
        ]
    except OSError:
        return [{"line": line} for line in _jobhunt("list", "-s", "all", "-n", "40").splitlines()]


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
    subprocess.Popen(
        ["gio", "open", settings()["employment_url"]],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"opened": settings()["employment_url"]}


def mark(job: str, status: str, note: str = "") -> str:
    """Records a job's progress: shortlisted, applied, assessment, interview, offer, rejected, withdrawn, skipped."""
    allowed = {
        "shortlisted",
        "applied",
        "assessment",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
        "skipped",
    }
    if status not in allowed:
        raise ValueError(f"status must be one of {', '.join(sorted(allowed))}")
    return _jobhunt("set", job, status, *([note] if note else []))


def status_digest() -> str:
    """The written status digest: what needs attention, new matches and the pipeline (printed, not emailed)."""
    return _jobhunt("digest", "--dry-run", timeout=120)


def matches(min_score: float = 60, limit: int = 8) -> str:
    """The best unreviewed matches, best first, each with its id."""
    return _jobhunt("list", "-m", f"{min_score:g}", "-n", str(int(limit)))


def shortlist(job: str, note: str = "") -> str:
    """Marks a job as worth applying for, so its pack is drafted next."""
    return mark(job, "shortlisted", note)


def todo_add(text: str) -> str:
    """Adds an item to the job-search to-do list; returns the list."""
    text = text.strip()
    if not text:
        raise ValueError("the to-do needs some text")
    return _jobhunt("todo", "add", "--", text)


def pack(job: str) -> dict:
    """Drafts the application pack for one job; returns the pack's files and jobhunt's output."""
    output = _jobhunt("pack", job, timeout=PACK_TIMEOUT)
    pack_md = next(
        (Path(line.strip()) for line in output.splitlines() if line.strip().endswith("pack.md")),
        None,
    )
    files = [pack_md, *sorted(pack_md.parent.glob("*.pdf"))] if pack_md and pack_md.exists() else []
    return {
        "pack": str(pack_md) if pack_md else None,
        "files": [str(f) for f in files],
        "output": output[-1500:],
    }
