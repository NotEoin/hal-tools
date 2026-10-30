"""Command line of the work pack: `hal-work mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "work"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "files": "halfiles",
    "dev": "haldev",
    "lang": "hallang",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the work pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv)
