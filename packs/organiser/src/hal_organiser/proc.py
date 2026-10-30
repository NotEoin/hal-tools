"""Text-mode subprocess helper for the organiser pack, a thin layer over `halkit.proc.run`.

`halkit.proc.run` returns bytes and kills the whole process group on a timeout (REQ-SYS-15).
Pack code wants text and no raised exit status (it reads `returncode` itself), so the decoding
and the `check=False` default live here once instead of in every module.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from halkit.proc import ProcTimeout
from halkit.proc import run as _run

__all__ = ["ProcTimeout", "completed"]


def completed(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    input: str | None = None,  # same name as subprocess.run
) -> subprocess.CompletedProcess[str]:
    """Runs `argv` with no shell and returns the result with stdout and stderr decoded.

    A non-zero exit does not raise; the caller reads `returncode`. Raises `ProcTimeout` after
    killing the process group, and `OSError` when the program cannot start.
    """
    done = _run(
        argv,
        timeout=timeout,
        cwd=None if cwd is None else Path(cwd),
        env=env,
        input=None if input is None else input.encode(),
        check=False,
    )
    return subprocess.CompletedProcess(
        done.args,
        done.returncode,
        done.stdout.decode(errors="replace"),
        done.stderr.decode(errors="replace"),
    )
