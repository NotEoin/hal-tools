"""Command line of the comms pack: `hal-comms mcp|tools|call|doctor`, from `halhub.pack`.

The subcommands are hal-hub's own, limited to this pack's modules, so a call goes through the
same policy and audit as any other (REQ-PACK-24: only declared tool names resolve).
"""

from collections.abc import Sequence

from halhub import pack

PACK = "comms"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "mail": "halmail",
    "phone": "halphone",
    "telegram": "haltelegram",
}


def _telegram(argv: list[str]) -> int:
    """Run the Telegram bridge, or save its token, show status, unpair."""
    from haltelegram.cli import (
        main as run,
    )

    return run(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the comms pack command line and returns its exit code."""
    return pack.main(PACK, tuple(MODULES), argv, extra={"telegram": _telegram})
