"""Settings for halshell: the [shell] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

TABLE = config.register(
    config.Table(
        "shell",
        (
            config.Key("timeout_s", int, 20, doc="Seconds a read-only shell_look command may run"),
            config.Key("max_output", int, 65536, doc="Cap on bytes read from a shell tool"),
            config.Key("max_timeout_s", int, 600, doc="Upper bound for a shell_run timeout"),
        ),
        owner="hal-system",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def shared() -> Mapping[str, object]:
    """Returns the shared `[hal]` table (models, vault, user name)."""
    return config.hal()
