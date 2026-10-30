"""Connects a CalDAV account (such as Apple iCloud) from a terminal, asking for the password
privately.

    hal-organiser calendar-connect [--url URL] [--username U] [--push-to NAME]

The password is read with getpass, so it is never echoed, never an argument and never in shell
history or a conversation. The credentials are tested before anything is saved; then you choose
the calendar new events go to, and one sync runs.
"""

from __future__ import annotations

import argparse
import getpass

from . import tools
from .caldav import CalDAVError

ICLOUD = "https://caldav.icloud.com"
ATTEMPTS = 3


def _choose(cals: list[dict], default: int, ask, out) -> dict:
    """Asks which calendar new events go to, by number or name; Enter keeps the default."""
    for _ in range(ATTEMPTS):
        try:
            answer = ask(f"Which calendar should Hal put new events in? [{default + 1}] ").strip()
        except EOFError:
            answer = ""
        if not answer:
            return cals[default]
        if answer.isdigit() and 1 <= int(answer) <= len(cals):
            return cals[int(answer) - 1]
        named = [c for c in cals if c["name"].lower() == answer.lower()]
        if named:
            return named[0]
        out(f"Type a number from 1 to {len(cals)}, or press Enter for {cals[default]['name']}.")
    return cals[default]


def main(argv: list[str] | None = None, ask=input, secret=getpass.getpass, out=print) -> int:
    parser = argparse.ArgumentParser(
        prog="hal-organiser calendar-connect",
        description="Connect Hal's calendar to a CalDAV account such as Apple iCloud.",
    )
    parser.add_argument("--url", default=ICLOUD, help=f"CalDAV server (default {ICLOUD})")
    parser.add_argument(
        "--username", default="", help="account name; for iCloud, your Apple ID email"
    )
    parser.add_argument(
        "--push-to", default="", help="calendar new events go to (asked if not given)"
    )
    args = parser.parse_args(argv)

    username = args.username.strip()
    while not username:
        try:
            username = ask("Apple ID email (or CalDAV username): ").strip()
        except EOFError:
            out("No username given; nothing was saved.")
            return 1
    if args.url == ICLOUD:
        out(
            "Use an app-specific password from appleid.apple.com "
            "(Sign-In and Security > App-Specific Passwords), not your Apple ID password."
        )
    result = None
    for attempt in range(ATTEMPTS):
        try:
            password = secret("App-specific password (not shown as you type): ").strip()
        except EOFError:
            password = ""
        if not password:
            out("No password given; nothing was saved.")
            return 1
        try:
            result = tools.setup_caldav(username, password, args.url, args.push_to)
            break
        except CalDAVError as e:
            out(f"Could not connect: {e}.")
            if "refused" not in str(e):
                out("Nothing was saved.")
                return 1
            out(
                "Check the email, and that you pasted an app-specific password,"
                " not your usual one."
                + (" Try again." if attempt < ATTEMPTS - 1 else " Nothing was saved.")
            )
    if result is None:
        return 1

    cals = result["calendars"]
    if not cals:
        out("Connected and saved, but the account has no event calendars.")
        return 1
    out(f"Connected as {username}. Calendars:")
    for n, c in enumerate(cals, 1):
        out(f"  {n}. {c['name']}" + ("" if c.get("writable", True) else "  (read-only)"))
    wanted = args.push_to.lower()
    default = next((n for n, c in enumerate(cals) if wanted and c["name"].lower() == wanted), None)
    if default is None:
        default = next((n for n, c in enumerate(cals) if c.get("writable", True)), 0)
    target = _choose(cals, default, ask, out)
    if not target.get("writable", True):
        out(f"Note: {target['name']} looks read-only, so new events may not reach it.")
    tools.write_caldav_settings({"push_to": target["name"]})
    out(f"New events will go to {target['name']}. Syncing...")
    try:
        counts = tools.sync()
    except CalDAVError as e:
        out(f"Saved, but the first sync failed: {e}.")
        return 1
    out(
        f"Synced: {counts['pulled']} pulled, {counts['pushed']} pushed, "
        f"{counts['deleted']} deleted. "
        f"The reminder service syncs every {tools.settings().get('sync_minutes', 15)} minutes."
    )
    return 0
