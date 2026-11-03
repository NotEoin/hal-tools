"""hal-jobs' tools: the job search, through the command line that Hal Employment ships.

jobhunt lives in its own repository (configured as [jobs].jobhunt_root); this module
only calls it, so it holds no job data itself. Applications are still made in
Hal Employment, where every submit is pressed by the owner.
"""

from __future__ import annotations

import os
from pathlib import Path

from hal_jobs import proc

from .settings import jobhunt_root, settings

SYSTEM_PYTHON = "/usr/bin/python3"
PORTAL_TIMEOUT = 15  # seconds; the portal answers at once, or shows its app chooser and returns
PACK_TIMEOUT = 1800  # seconds; drafting a pack runs the local model and searches the web


def _jobhunt(*args: str, timeout: float = 600) -> str:
    root = jobhunt_root()
    if not (root / "jobhunt").is_dir():
        raise RuntimeError(f"jobhunt not found at {root}; set [jobs].jobhunt_root")
    venv_python = root / ".venv" / "bin" / "python"  # holds Playwright; the same pick as the unit
    python = str(venv_python) if os.access(venv_python, os.X_OK) else SYSTEM_PYTHON
    done = proc.completed([python, "-m", "jobhunt", *args], cwd=root, timeout=timeout)
    if done.returncode:
        raise RuntimeError((done.stderr or done.stdout).strip()[-400:])
    return done.stdout.strip()


def queue() -> dict:
    """The jobs waiting to be applied for, best first, as the lines `jobhunt queue` prints."""
    return {"jobs": _jobhunt("queue").splitlines()}


def applications() -> list[dict]:
    """Applications in progress and sent, by stage, as the lines `jobhunt list` prints."""
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
    """Returns the job counts from the Hal Employment app."""
    return _jobhunt("stats")


def open_employment() -> dict:
    """Opens Hal Employment in the browser, through the desktop's OpenURI portal.

    Hal runs tools in a sandbox with its own process and network namespaces, so a browser
    started from here (`gio open`, `xdg-open`) dies with the sandbox or cannot reach the app, and
    `systemd-run --user` cannot reach the user manager. The portal is asked over the session bus
    and launches the browser in the user's session instead. Raises when the portal refuses or is
    missing, so Hal never reports a page it did not open.
    """
    url = settings()["employment_url"]
    try:
        done = proc.completed(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.freedesktop.portal.Desktop",
                "--object-path",
                "/org/freedesktop/portal/desktop",
                "--method",
                "org.freedesktop.portal.OpenURI.OpenURI",
                "",
                url,
                "{}",
            ],
            timeout=PORTAL_TIMEOUT,
        )
    except OSError as exc:
        raise RuntimeError(
            f"could not open {url}: gdbus is missing ({exc}); open it in a browser"
        ) from exc
    if done.returncode:
        detail = (done.stderr or done.stdout).strip()[-200:]
        raise RuntimeError(f"the desktop did not open {url} ({detail}); open it in a browser")
    return {"opened": url}


def mark(job: str, status: str, note: str = "") -> str:
    """Records a job's progress; `status` is one of the pipeline stages."""
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
    return _jobhunt("set", "--", job, status, *([note] if note else []))


def status_digest() -> str:
    """The written status digest: what needs attention, new matches and the pipeline."""
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
    output = _jobhunt("pack", "--", job, timeout=PACK_TIMEOUT)
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
