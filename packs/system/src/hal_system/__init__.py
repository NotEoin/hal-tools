"""Command line of the system pack: `hal-system mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "system"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "system": "halsys",
    "power": "halpower",
    "packages": "halpkgs",
    "devices": "haldevices",
    "network": "halnet",
    "models": "halmodels",
    "shell": "halshell",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the system pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv)
