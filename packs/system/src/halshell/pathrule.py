"""The read-path rule for `shell_look` arguments (REQ-PACK-21).

The hub's own path rule is not importable by packs yet, so this module applies the same shape
with `halkit.paths.confine`: read roots minus a built-in deny list. The single `command` string
escapes the broker's per-parameter path check, which is why the pack checks again. Hard-deny
paths hold keys, Hal's own state and the kernel pseudo-filesystems.
"""

from __future__ import annotations

from pathlib import Path

from halkit import paths

HARD_DENY = ("/proc", "/sys", "/dev")
HOME_DENY = (".ssh", ".gnupg", ".config/hal", ".local/state/hal", ".local/share/hal", ".aws")


def read_roots() -> list[Path]:
    """Directories `shell_look` may read: the home directory and the temporary directory."""
    return [Path.home(), Path("/tmp")]  # noqa: S108 - a read root, not a file created here


def deny_paths() -> list[Path]:
    """Paths refused even inside a read root."""
    home = Path.home()
    dirs = [paths.state_dir(), paths.config_dir()]
    try:
        dirs.append(paths.runtime_dir())
    except (paths.RuntimeDirMissing, OSError):
        pass  # no runtime dir on this host, so nothing to protect there
    return [Path(p) for p in HARD_DENY] + [home / p for p in HOME_DENY] + dirs


def read_ok(path: Path) -> str | None:
    """None when `path` may be read by `shell_look`, else the reason it may not."""
    try:
        paths.confine(str(path), read_roots(), deny_paths())
    except paths.PathNotAllowed as exc:
        return str(exc)
    return None
