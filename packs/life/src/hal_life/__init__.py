"""Command line of the life pack: `hal-life mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "life"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "contacts": "halcontacts",
    "habits": "halhabits",
    "ledger": "halledger",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the life pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv)
