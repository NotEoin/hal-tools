"""Tells whether the tools run under WSL2, from the kernel's `osrelease`.

WSL2 kernels say `microsoft-standard-WSL2`. A few tools behave differently there (no power
state, no PipeWire, no login session), so they check this and fail with advice. The pack keeps
its own copy, like its `proc.py`, because each pack installs into its own environment.
`$HAL_TOOLS_OSRELEASE` names a file that replaces `/proc/sys/kernel/osrelease`, which is how
the tests fake WSL2.
"""

from __future__ import annotations

import os
from pathlib import Path

OSRELEASE = Path("/proc/sys/kernel/osrelease")
OSRELEASE_ENV = "HAL_TOOLS_OSRELEASE"
DOCS_HINT = "docs/howto/run-on-windows-with-wsl2.md in hal-tools"


def is_wsl2() -> bool:
    """True when the kernel release names Microsoft or WSL; False when it cannot be read."""
    path = Path(os.environ.get(OSRELEASE_ENV) or OSRELEASE)
    try:
        text = path.read_text(encoding="ascii", errors="replace").strip()
    except OSError:
        return False
    return "microsoft" in text.lower() or "WSL" in text
