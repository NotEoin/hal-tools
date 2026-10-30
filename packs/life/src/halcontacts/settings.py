"""Settings for halcontacts: the [contacts] table of the shared config (`halkit.config`).

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config

TABLE = config.register(
    config.Table(
        "contacts",
        (config.Key("folder", str, "People", doc="Vault folder that holds the contact notes"),),
        owner="hal-life",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def vault() -> Path:
    """Returns the vault directory from the shared `[hal]` table."""
    return Path(str(config.hal()["vault"])).expanduser()
