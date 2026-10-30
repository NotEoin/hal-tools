"""Settings for hal-calendar: the [calendar] table of the shared config, read through
`halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "calendar",
        (
            config.Key("timezone", str, "Europe/London", doc="IANA timezone for events"),
            config.Key("default_reminders", list, [15], doc="Minutes before an event to remind"),
            config.Key("all_day_reminder_hour", int, 8, doc="Hour of day for all-day reminders"),
            config.Key("sync_minutes", int, 15, doc="Minutes between CalDAV syncs"),
            config.Key(
                "import_roots",
                list,
                ["~/Documents", "~/Downloads"],
                doc="Folders `calendar_import` and `calendar_export` may use",
            ),
            config.Key(
                "caldav",
                dict,
                {},
                doc="CalDAV account: url, username, password_file, calendars, push_to",
            ),
        ),
        owner="hal-organiser",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "calendar"
    path.mkdir(parents=True, exist_ok=True)
    return path
