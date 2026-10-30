"""Settings for hal-tasks: the [tasks] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "tasks",
        (
            config.Key(
                "vault_note", str, "Tasks.md", doc="Vault note the task list is mirrored to"
            ),
            config.Key("remind_minutes", int, 10, doc="Minutes before a due task to remind"),
        ),
        owner="hal-organiser",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def vault() -> Path:
    """Returns the vault directory from the shared `[hal]` table."""
    return Path(str(config.hal()["vault"])).expanduser()


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "tasks"
    path.mkdir(parents=True, exist_ok=True)
    return path
