"""Evening nudge: once a day, after [habits].nudge_hour, lists habits not done yet.

    python -m halhabits.nudge      (run by the systemd timer)
"""
from . import tools
from .notify import notify


def main() -> None:
    left = [h for h in tools.today() if not h["complete"]]
    if left:
        notify("Habits still to do", "; ".join(f"{h['habit']} ({h['done']})" for h in left))


if __name__ == "__main__":
    main()
