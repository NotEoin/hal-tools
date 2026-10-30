"""Settings for halmail: the [mail] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

TABLE = config.register(
    config.Table(
        "mail",
        (
            config.Key(
                "default", str, "", doc="Account used when none is named (empty: the only one)"
            ),
            config.Key(
                "accounts",
                dict,
                {},
                doc="Accounts (none by default): address, imap, smtp, password_file",
            ),
        ),
        owner="hal-comms",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def shared() -> Mapping[str, object]:
    """Returns the shared `[hal]` table (models, vault, user name)."""
    return config.hal()
