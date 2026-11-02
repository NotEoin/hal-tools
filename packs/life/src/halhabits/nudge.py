"""Evening nudge: once a day, after [habits].nudge_hour, lists habits not done yet.

python -m halhabits.nudge      (run by the systemd timer)
"""

from halkit.notify import send

from . import tools


def main() -> None:
    """Sends a reminder listing today's habits that are not done, if any."""
    left = [h for h in tools.today() if not h["complete"]]
    if left:
        send(
            "Habits still to do",
            "; ".join(f"{h['habit']} ({h['done']})" for h in left),
            source="habits",
        )


if __name__ == "__main__":
    main()
