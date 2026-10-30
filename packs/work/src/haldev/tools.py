"""hal-dev's tools: the state of every git repository, TODOs, tests and GitHub.

Repositories are found under the configured roots. Everything here reads,
except running a project's tests. It never commits, pushes or changes a branch.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from hal_work import proc
from halkit import paths

from .settings import settings

SKIP = {"node_modules", ".venv", "venv", "__pycache__", "site-packages", "GPT-SoVITS"}


def _git(repo: Path, *args: str, timeout: float = 30) -> str:
    done = proc.completed(["git", "-C", str(repo), *args], timeout=timeout)
    return done.stdout.strip()


def _repos() -> list[Path]:
    found = []
    for root in settings()["roots"]:
        base = Path(root).expanduser()
        if not base.is_dir():
            continue
        for git in base.glob("**/.git"):
            parts = set(git.relative_to(base).parts)
            if (
                not parts & SKIP
                and len(git.relative_to(base).parts) <= int(settings()["depth"]) + 1
            ):
                found.append(git.parent)
    return sorted(set(found))


def _find(repo: str) -> Path:
    """A repository by name, or by path when the path is inside `[dev].roots`."""
    if "/" in repo or repo.startswith("~"):
        p = paths.confine(repo, [Path(r) for r in settings()["roots"]], [])
        if not (p / ".git").exists():
            raise ValueError(f"{repo} is not a git repository")
        return p
    hits = [r for r in _repos() if r.name.lower() == repo.lower()] or [
        r for r in _repos() if repo.lower() in r.name.lower()
    ]
    if not hits:
        raise ValueError(f"no repository called {repo!r}")
    return hits[0]


def repos(dirty_only: bool = False) -> list[dict]:
    """Every repository: branch, dirty files, commits ahead or behind upstream, last commit."""
    out = []
    for r in _repos():
        status = _git(r, "status", "--porcelain=v1", "--branch")
        lines = status.splitlines()
        head = lines[0] if lines else ""
        ahead = re.search(r"ahead (\d+)", head)
        behind = re.search(r"behind (\d+)", head)
        changed = len(lines) - 1
        if dirty_only and not changed and not ahead:
            continue
        out.append(
            {
                "repo": r.name,
                "path": str(r),
                "branch": head[3:].split("...")[0],
                "uncommitted": changed,
                "ahead": int(ahead.group(1)) if ahead else 0,
                "behind": int(behind.group(1)) if behind else 0,
                "remote": bool(_git(r, "remote")),
                "last_commit": _git(r, "log", "-1", "--format=%ar: %s"),
            }
        )
    return out


def status(repo: str) -> dict:
    r = _find(repo)
    return {
        "repo": r.name,
        "status": _git(r, "status", "--short", "--branch").splitlines()[:40],
        "stash": _git(r, "stash", "list").splitlines()[:5],
    }


def log(repo: str, limit: int = 10) -> list[str]:
    return _git(
        _find(repo), "log", f"-{int(limit)}", "--format=%h %ad %s", "--date=short"
    ).splitlines()


def diff(repo: str) -> dict:
    """What has changed and not been committed, as a summary and the start of the diff."""
    r = _find(repo)
    return {
        "stat": _git(r, "diff", "--stat", "HEAD").splitlines()[-20:],
        "diff": _git(r, "diff", "HEAD")[:6000],
    }


def todos(repo: str = "", limit: int = 40) -> list[dict]:
    """TODO, FIXME and HACK comments in one repository, or all of them."""
    targets = [_find(repo)] if repo else _repos()
    out = []
    for r in targets:
        for line in _git(r, "grep", "-n", "-I", "-E", r"\b(TODO|FIXME|HACK|XXX)\b").splitlines():
            path, _, rest = line.partition(":")
            num, _, text = rest.partition(":")
            out.append(
                {"repo": r.name, "file": path, "line": int(num or 0), "text": text.strip()[:160]}
            )
            if len(out) >= int(limit):
                return out
    return out


def run_tests(repo: str) -> dict:
    """Runs a project's tests (pytest, unittest, npm or cargo) and reports the result."""
    r = _find(repo)
    pyproject = (
        (r / "pyproject.toml").read_text(errors="ignore") if (r / "pyproject.toml").exists() else ""
    )
    if (r / "package.json").exists() and '"test"' in (r / "package.json").read_text():
        cmd = ["npm", "test", "--silent"]
    elif (r / "Cargo.toml").exists():
        cmd = ["cargo", "test", "-q"]
    elif (r / "pytest.ini").exists() or (r / "conftest.py").exists() or "pytest" in pyproject:
        cmd = ["python3", "-m", "pytest", "-q"]
    elif (r / "tests").is_dir():
        cmd = ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"]
    else:
        raise ValueError(f"{r.name} has no tests that hal-dev recognises")
    done = proc.completed(cmd, cwd=r, timeout=1800)
    tail = (done.stdout + done.stderr).strip().splitlines()[-15:]
    return {
        "repo": r.name,
        "command": " ".join(cmd),
        "passed": done.returncode == 0,
        "output": tail,
    }


def github(kind: str = "prs", repo: str = "") -> list[str]:
    """Open pull requests or issues on GitHub (through the gh command), or notifications."""
    if not shutil.which("gh"):
        raise RuntimeError("install the GitHub command line (gh) and run 'gh auth login'")
    where = ["-R", repo] if repo else []
    if kind == "notifications":
        cmd = [
            "gh",
            "api",
            "notifications",
            "--jq",
            '.[] | .repository.full_name + ": " + .subject.title',
        ]
    elif kind == "issues":
        cmd = (
            ["gh", "search", "issues", "--involves=@me", "--state=open", "--limit", "20"]
            if not repo
            else ["gh", "issue", "list", *where]
        )
    else:
        cmd = (
            ["gh", "search", "prs", "--involves=@me", "--state=open", "--limit", "20"]
            if not repo
            else ["gh", "pr", "list", *where]
        )
    done = proc.completed(cmd, timeout=60)
    if done.returncode:
        raise RuntimeError(done.stderr.strip()[-300:])
    return done.stdout.strip().splitlines()[:30]
