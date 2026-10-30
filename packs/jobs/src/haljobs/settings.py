"""Settings for haljobs: the [jobs] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

import logging
from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

log = logging.getLogger("hal-jobs")
_warned = False  # the legacy-default warning is logged once per process

TABLE = config.register(
    config.Table(
        "jobs",
        (
            config.Key(
                "jobhunt_root",
                str,
                "~/src/employment-helper",
                deprecated_alias="jobhunt",
                doc="Directory of the jobhunt checkout",
            ),
            config.Key(
                "employment_url", str, "http://127.0.0.1:8737/", doc="Hal Employment API URL"
            ),
        ),
        owner="hal-jobs",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def jobhunt_root() -> Path:
    """Returns the jobhunt checkout; logs one warning if `[jobs]` is absent (old default)."""
    global _warned
    if not _warned and "jobs" not in config.read_toml(paths.config_file()):
        _warned = True
        log.warning(
            "[jobs] is not in the config; using the old default jobhunt_root. "
            "Add [jobs] jobhunt_root = ... to %s",
            paths.config_file(),
        )
    return Path(str(settings()["jobhunt_root"])).expanduser()
