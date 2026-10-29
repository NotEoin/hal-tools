"""The job-search commands: hal-jobs and hal-briefing tools, through hal-hub.

Every command maps to one tool, so jobhunt and Hal Employment stay behind
hal-jobs and this bridge never runs them itself.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Jobs:
    """Runs job commands through a hal-hub module (halhub) when it has the tool."""

    def __init__(self, hub) -> None:
        self.hub = hub

    def has(self, tool: str) -> bool:
        return bool(self.hub and self.hub.get(tool))

    def call(self, name: str, **args) -> tuple[object, str | None]:
        """Calls a tool; returns (result, None), or (None, a message saying why it couldn't)."""
        if not self.has(name):
            module = name.split("_")[0]
            return None, f"The {module} extension isn't installed (hal ext add {module})."
        out = self.hub.call(name, args)
        if "error" in out:
            return None, f"That didn't work: {out['error']}"
        return out.get("result"), None

    def tool(self, name: str, **args) -> str:
        result, problem = self.call(name, **args)
        return problem or render(result)

    def status(self) -> str:
        return self.tool("jobs_status")

    def brief(self) -> str:
        kind = "morning" if datetime.now().hour < 14 else "evening"
        return self.tool("briefing_build", kind=kind)

    def matches(self) -> str:
        return self.tool("jobs_matches")

    def queue(self) -> str:
        return self.tool("jobs_queue")

    def todo(self, text: str = "") -> str:
        return self.tool("jobs_todo_add", text=text) if text else self.tool("jobs_todo")

    def discard(self, job: str) -> str:
        return self.tool("jobs_mark", job=job, status="skipped")

    def applied(self, job: str) -> str:
        return self.tool("jobs_mark", job=job, status="applied")

    def shortlist(self, job: str) -> str:
        return self.tool("jobs_shortlist", job=job)

    def pack(self, job: str) -> tuple[str, list[Path]]:
        """Drafts an application pack; returns jobhunt's output (or why it failed) and the files to send."""
        result, problem = self.call("jobs_pack", job=job)
        if problem:
            return problem, []
        if not isinstance(result, dict):
            return render(result), []
        files = [Path(f) for f in result.get("files") or [] if Path(f).is_file()]
        return result.get("output") or "", files


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
