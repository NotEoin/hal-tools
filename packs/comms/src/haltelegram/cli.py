"""Human-only Telegram commands, run as `hal-comms telegram` (never a tool).

hal-comms telegram                run the bridge (the unit runs `python -m haltelegram.cli`)
hal-comms telegram token TOKEN    save the bot token from @BotFather (owner-only file)
hal-comms telegram status         whether a token is saved and a chat paired
hal-comms telegram unpair         forget the paired chat; the next start shows a new code
"""

import json
import re
import sys

from . import settings as config
from . import tools

TOKEN = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


def save_token(token: str) -> str:
    """Saves the bot token; raises ValueError if it does not look like one."""
    token = token.strip()
    if not TOKEN.match(token):
        raise ValueError(
            "that doesn't look like a bot token (digits, a colon, then about 35 characters)"
        )
    config.write_private(config.token_file(), token)
    return f"saved to {config.token_file()}"


def main(argv: list[str] | None = None) -> int:
    """Runs one Telegram command (default: the bridge) and returns its exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "run"
    if command in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if command == "run":
        from .bridge import run

        return run()
    if command == "token" and len(argv) == 2:
        try:
            print(save_token(argv[1]))
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2
        return 0
    if command == "status":
        print(json.dumps(tools.status(), indent=2))
        return 0
    if command == "unpair":
        config.chat_file().unlink(missing_ok=True)
        print("unpaired; restart the bridge to get a new pairing code")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
