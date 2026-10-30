"""Command line of the desktop pack: `hal-desktop mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "desktop"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "desktop": "haldesk",
    "screen": "halscreen",
    "media": "halmedia",
    "rgb": "halrgb",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the desktop pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv)
