"""Command line of the online pack: `hal-online MODULE [TOOL [key=value ...]]`.

Interim shim: it hands the arguments to the module's own `python -m` entry point. The pack CLI
of hal-hub (`mcp|tools|call|doctor`) replaces it in step H-15.
"""

import importlib
import sys
from collections.abc import Sequence

PACK = "online"
# Module name -> importable package, the same pairs as the `hal.packs` entry points.
MODULES = {
    "web": "halweb",
    "feeds": "halfeeds",
}


def main(argv: Sequence[str] | None = None) -> int:
    """Runs one module's command line and returns its exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(f"usage: hal-{PACK} MODULE [TOOL [key=value ...]]")
        print("modules: " + ", ".join(MODULES))
        return 0 if args else 2
    package = MODULES.get(args[0])
    if package is None:
        print(f"hal-{PACK}: no module {args[0]!r}; modules: {', '.join(MODULES)}", file=sys.stderr)
        return 2
    entry = importlib.import_module(f"{package}.__main__")
    return entry.main(args[1:])
