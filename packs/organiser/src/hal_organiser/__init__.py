"""Command line of the organiser pack: `hal-organiser mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "organiser"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "calendar": "halcal",
    "tasks": "haltasks",
    "clock": "halclock",
    "notify": "halnotify",
    "briefing": "halbrief",
    "routines": "halroutines",
}


def _calendar_connect(argv: list[str]) -> int:
    """Connect a CalDAV account (asks for the password)."""
    from halcal.connect import (
        main as run,
    )

    return run(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the organiser pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv, extra={"calendar-connect": _calendar_connect})
