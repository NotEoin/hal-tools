"""The read-path rule for `shell_look` arguments (REQ-PACK-21), taken from the hub's policy.

The single `command` string escapes the broker's per-parameter path check, so the pack checks
every path it finds with `halhub.policy.check_host_path`, the same rule `decide` applies to a
`format = "path"` argument (REQ-SEC-100). The read roots are `[tools.shell_look].read_roots` in
`policy.toml`, else `[paths].read_roots`. The policy file is re-read only when it changes, so a
long-lived worker sees an edit and a hot loop does not parse TOML per argument.
"""

from __future__ import annotations

import logging
from pathlib import Path

from halhub.policy import Policy, active_workspaces, check_host_path, load_policy
from halkit import paths

log = logging.getLogger(__name__)

TOOL = "shell_look"  # the policy section whose roots apply

_cache: dict[tuple[Path, int, Path], Policy] = {}


def _policy() -> Policy:
    """The loaded policy, cached on the file's mtime and the home directory."""
    file, home = paths.policy_file(), Path.home()
    try:
        stamp = file.stat().st_mtime_ns
    except FileNotFoundError:
        stamp = 0  # no file means the built-in defaults
    key = (file, stamp, home)
    if key not in _cache:
        _cache.clear()
        _cache[key] = load_policy(file, home=home)
    return _cache[key]


def read_ok(path: Path) -> str | None:
    """None when `path` may be read by `shell_look`, else the deny rule that refused it."""
    rule, _ = check_host_path(
        str(path),
        access="read",
        tool=TOOL,
        policy=_policy(),
        workspaces=active_workspaces(),
        home=Path.home(),
    )
    return rule
