"""`python -m halbrief`: the organiser pack command line limited to the briefing module.

`brief kind=K` delivers one briefing at once. It is the briefing timers' entry point: `call
briefing_deliver` needs `--yes` from a person at a terminal, and a timer the user enabled is
already that approval.
"""

import sys

from halhub import pack

KINDS = ("morning", "jobs", "evening")  # the kinds the briefing timers start


def brief(args: list[str]) -> int:
    """Runs `brief kind=K`: builds the briefing and speaks, pushes and saves it."""
    if len(args) != 1 or not args[0].startswith("kind="):
        print("usage: python -m halbrief brief kind=" + "|".join(KINDS), file=sys.stderr)
        return 2
    kind = args[0].removeprefix("kind=")
    if kind not in KINDS:
        print(f"unknown briefing kind {kind!r}; known: {', '.join(KINDS)}", file=sys.stderr)
        return 2
    from halbrief import tools

    tools.brief(kind)
    return 0


if __name__ == "__main__":
    sys.exit(pack.main("organiser", ("briefing",), extra={"brief": brief}))
