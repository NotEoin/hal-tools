"""The job-search commands: hal-jobs and hal-briefing tools through hal-hub, jobhunt where they stop.

hal-jobs covers the queue, the to-do list and marking jobs applied or discarded.
Listing matches, adding a to-do, shortlisting, the written status digest and
drafting a pack have no hal-jobs tool yet, so those run jobhunt's command line
in [jobs].jobhunt_root.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from . import config


def jobhunt(*args: str, timeout: float = 900) -> str:
    """Runs a jobhunt command and returns its output."""
    root = config.jobhunt_root()
    if not (root / "jobhunt").is_dir():
        return f"jobhunt isn't at {root}; set [jobs].jobhunt_root in ~/.config/hal/config.toml."
    done = subprocess.run(["/usr/bin/python3", "-m", "jobhunt", *args], cwd=root,
                          capture_output=True, text=True, timeout=timeout)
    return (done.stdout + done.stderr).strip()


class Jobs:
    """Runs job commands through a hal-hub module (halhub) when it has the tool."""

    def __init__(self, hub) -> None:
        self.hub = hub

    def has(self, tool: str) -> bool:
        return bool(self.hub and self.hub.get(tool))

    def tool(self, name: str, **args) -> str:
        if not self.has(name):
            module = name.split("_")[0]
            return f"The {module} extension isn't installed (hal ext add {module})."
        out = self.hub.call(name, args)
        if "error" in out:
            return f"That didn't work: {out['error']}"
        return render(out.get("result"))

    def status(self) -> str:
        return jobhunt("digest", "--dry-run")

    def brief(self) -> str:
        kind = "morning" if datetime.now().hour < 14 else "evening"
        return self.tool("briefing_build", kind=kind)

    def matches(self) -> str:
        return jobhunt("list", "-m", "60", "-n", "8")

    def queue(self) -> str:
        return self.tool("jobs_queue")

    def todo(self, text: str = "") -> str:
        return jobhunt("todo", "add", text) if text else self.tool("jobs_todo")

    def discard(self, job: str) -> str:
        return self.tool("jobs_mark", job=job, status="skipped")

    def applied(self, job: str) -> str:
        return self.tool("jobs_mark", job=job, status="applied")

    def shortlist(self, job: str) -> str:
        return jobhunt("set", job, "shortlisted")

    def pack(self, job: str) -> tuple[str, list[Path]]:
        """Drafts an application pack; returns the output's tail and the files to send."""
        output = jobhunt("pack", job, timeout=1800)
        pack_md = next((Path(line.strip()) for line in output.splitlines() if line.strip().endswith("pack.md")), None)
        files = []
        if pack_md and pack_md.exists():
            files = [pack_md, *sorted(pack_md.parent.glob("*.pdf"))]
        return output[-1500:], files


def render(result) -> str:
    """Turns a tool result into chat text."""
    if result is None:
        return "Done."
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and isinstance(result.get("jobs"), list):
        lines = [_job_line(j) for j in result["jobs"]]
        head = f"{result['ready']} ready, {result.get('reserve', 0)} in reserve\n" if "ready" in result else ""
        return head + ("\n".join(lines) or "Nothing queued.")
    if isinstance(result, dict) and len(result) == 1:
        return render(next(iter(result.values())))
    if isinstance(result, list):
        return "\n".join(_job_line(x) if isinstance(x, dict) else str(x) for x in result) or "Nothing."
    return json.dumps(result, indent=1, default=str)


def _job_line(job) -> str:
    if not isinstance(job, dict):
        return str(job)
    if "line" in job:
        return job["line"]
    score = f"{job['score']:.0f}  " if isinstance(job.get("score"), (int, float)) else ""
    where = f" ({job['location']})" if job.get("location") else ""
    stage = f" [{job['status']}]" if job.get("status") else ""
    return f"{score}{job.get('company', '?')}: {job.get('title', '')}{where}{stage}"
