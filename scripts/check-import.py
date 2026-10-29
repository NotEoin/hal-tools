#!/usr/bin/env python3
"""Checks the imported history against the source extension repositories.

Verifies REQ-PACK-03 (every source commit is reachable with its author, author date and
subject, and every file sits at its mapped path) and REQ-PACK-05 (no root commit comes from
anywhere but the 29 mapped extensions). Usage: `check-import.py <extensions-dir>
[--replacements FILE]`. `--replacements` is the scrub list (`literal==>replacement` lines) kept
outside the repository; without it, a file that differs from its source is reported.

Stdlib only. Exits 0 when every check passes, 1 on any difference, 2 on a usage error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections import Counter
from pathlib import Path

GIT_TIMEOUT = 60  # seconds; a local log or show on a repository of this size takes well under 1

# (extension directory, package, pack, module): the mapping table of spec 08, in import order.
EXTENSIONS: tuple[tuple[str, str, str, str], ...] = (
    ("hal-briefing", "halbrief", "organiser", "briefing"),
    ("hal-calendar", "halcal", "organiser", "calendar"),
    ("hal-clock", "halclock", "organiser", "clock"),
    ("hal-notify", "halnotify", "organiser", "notify"),
    ("hal-routines", "halroutines", "organiser", "routines"),
    ("hal-tasks", "haltasks", "organiser", "tasks"),
    ("hal-contacts", "halcontacts", "life", "contacts"),
    ("hal-habits", "halhabits", "life", "habits"),
    ("hal-ledger", "halledger", "life", "ledger"),
    ("hal-mail", "halmail", "comms", "mail"),
    ("hal-phone", "halphone", "comms", "phone"),
    ("hal-telegram", "haltelegram", "comms", "telegram"),
    ("hal-web", "halweb", "online", "web"),
    ("hal-feeds", "halfeeds", "online", "feeds"),
    ("hal-desktop", "haldesk", "desktop", "desktop"),
    ("hal-screen", "halscreen", "desktop", "screen"),
    ("hal-media", "halmedia", "desktop", "media"),
    ("hal-rgb", "halrgb", "desktop", "rgb"),
    ("hal-system", "halsys", "system", "system"),
    ("hal-power", "halpower", "system", "power"),
    ("hal-packages", "halpkgs", "system", "packages"),
    ("hal-devices", "haldevices", "system", "devices"),
    ("hal-network", "halnet", "system", "network"),
    ("hal-models", "halmodels", "system", "models"),
    ("hal-shell", "halshell", "system", "shell"),
    ("hal-files", "halfiles", "work", "files"),
    ("hal-dev", "haldev", "work", "dev"),
    ("hal-lang", "hallang", "work", "lang"),
    ("hal-jobs", "haljobs", "jobs", "jobs"),
)
# Files the import drops: one root LICENSE and .gitignore replace the per-extension copies.
DROPPED = frozenset({"LICENSE", ".gitignore"})
IMPORT_SUBJECT = "Import {ext} history into {pack} pack"
Commit = tuple[str, str, str]  # author email, author date (ISO 8601), subject


def git(repo: Path, *args: str) -> str:
    """Runs `git -C repo args` and returns stdout; raises on a non-zero exit."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=GIT_TIMEOUT,
    )
    return done.stdout


def git_bytes(repo: Path, *args: str) -> bytes:
    """Runs `git -C repo args` and returns raw stdout."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=True, timeout=GIT_TIMEOUT
    )
    return done.stdout


def commits(repo: Path, *revs: str) -> list[Commit]:
    """Lists (author email, author date, subject) for the non-merge commits in `revs`."""
    out = git(repo, "log", "--no-merges", "--format=%ae%x1f%aI%x1f%s", *revs)
    rows = [line.split("\x1f") for line in out.splitlines() if line]
    return [(r[0], r[1], r[2]) for r in rows]


def mapped_path(path: str, package: str, pack: str, module: str) -> str | None:
    """Returns where the import puts a source path, or None when the import drops it."""
    if path in DROPPED:
        return None
    base = f"packs/{pack}"
    if path == "hal-module.toml":
        return f"{base}/src/{package}/hal-module.toml"
    if path == "README.md":
        return f"{base}/docs/{module}.md"
    prefixes = {
        f"{package}/": f"{base}/src/{package}/",
        "tests/": f"{base}/tests/",
        "systemd/": f"{base}/systemd/",
        "bin/": f"{base}/bin/",
        "desktop/": f"{base}/desktop/",
    }
    for old, new in prefixes.items():
        if path.startswith(old):
            return new + path[len(old) :]
    return path


def load_replacements(path: Path | None) -> list[tuple[bytes, bytes]]:
    """Reads `literal==>replacement` lines from the scrub list."""
    if path is None:
        return []
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "==>" in line:
            old, new = line.split("==>", 1)
            pairs.append((old.encode(), new.encode()))
    return pairs


def import_tip(tools: Path) -> str:
    """Returns the last import merge (or the first history's tip) on the first-parent chain."""
    out = git(tools, "log", "--first-parent", "--format=%H%x1f%s")
    for line in out.splitlines():
        sha, subject = line.split("\x1f", 1)
        if subject.startswith("Import hal-"):
            return sha
    raise RuntimeError("no 'Import hal-...' merge found on the first-parent chain of HEAD")


def check_commits(tools: Path, tip: str, ext_dir: Path, errors: list[str]) -> None:
    """Compares each source's commits with the commits its merge brought in."""
    for index, (ext, _package, pack, _module) in enumerate(EXTENSIONS):
        merge = git(
            tools,
            "log",
            "--first-parent",
            "--format=%H",
            f"--grep=^{IMPORT_SUBJECT.format(ext=ext, pack=pack)}$",
            tip,
        ).strip()
        if index == 0:
            first_merge = git(
                tools, "log", "--first-parent", "--format=%H", "--reverse", "--merges", tip
            ).split()[0]
            theirs = commits(tools, f"{first_merge}^1")
        elif merge:
            theirs = commits(tools, f"{merge}^2", f"^{merge}^1")
        else:
            errors.append(f"{ext}: no import merge found")
            continue
        ours = commits(ext_dir / ext, "HEAD")
        if Counter(ours) != Counter(theirs):
            errors.append(
                f"{ext}: source has {len(ours)} commits, import has {len(theirs)}; "
                "author, date or subject differ"
            )


def check_roots(tools: Path, tip: str, ext_dir: Path, errors: list[str]) -> None:
    """Checks that the root commits are exactly the sources' root commits (REQ-PACK-05)."""
    roots = git(tools, "rev-list", "--max-parents=0", "--all").split()
    theirs = Counter()
    for sha in roots:
        theirs.update(commits(tools, "-1", sha))
    ours = Counter()
    for ext, *_ in EXTENSIONS:
        for sha in git(ext_dir / ext, "rev-list", "--max-parents=0", "HEAD").split():
            ours.update(commits(ext_dir / ext, "-1", sha))
    if ours != theirs:
        errors.append(
            f"root commits differ: {len(roots)} in hal-tools, {sum(ours.values())} expected"
        )


def check_files(
    tools: Path,
    tip: str,
    ext_dir: Path,
    replacements: list[tuple[bytes, bytes]],
    errors: list[str],
) -> None:
    """Checks that each source file is at its mapped path with the scrubbed content."""
    expected: dict[str, tuple[str, bytes]] = {}
    for ext, package, pack, module in EXTENSIONS:
        src = ext_dir / ext
        for path in git(src, "ls-tree", "-r", "--name-only", "HEAD").splitlines():
            target = mapped_path(path, package, pack, module)
            if target is None:
                continue
            data = git_bytes(src, "show", f"HEAD:{path}")
            for old, new in replacements:
                data = data.replace(old, new)
            expected[target] = (ext, data)
    actual = set(git(tools, "ls-tree", "-r", "--name-only", tip).splitlines())
    for target in sorted(set(expected) - actual):
        errors.append(f"{expected[target][0]}: missing {target}")
    for target in sorted(actual - set(expected)):
        errors.append(f"unexpected file {target}")
    for target in sorted(set(expected) & actual):
        if git_bytes(tools, "show", f"{tip}:{target}") != expected[target][1]:
            errors.append(f"{expected[target][0]}: content differs at {target}")


def main(argv: list[str] | None = None) -> int:
    """Runs every check and prints one line per problem."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("extensions_dir", type=Path)
    parser.add_argument("--replacements", type=Path, help="scrub list kept outside the repository")
    args = parser.parse_args(argv)
    ext_dir = args.extensions_dir.expanduser().resolve()
    tools = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    try:
        tip = import_tip(tools)
        replacements = load_replacements(args.replacements)
        check_commits(tools, tip, ext_dir, errors)
        check_roots(tools, tip, ext_dir, errors)
        check_files(tools, tip, ext_dir, replacements, errors)
    except (subprocess.SubprocessError, OSError, RuntimeError) as exc:
        print(f"check-import: {exc}", file=sys.stderr)
        return 2
    for line in errors:
        print(line)
    if not errors:
        print(f"ok: {len(EXTENSIONS)} histories, root commits and files match")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
