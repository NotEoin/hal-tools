"""Settings for haljobs: the [jobs] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
`jobhunt_root` has no default: the jobhunt checkout lives wherever the user cloned it, so an
unset value raises `ConfigError` instead of guessing a path.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

TABLE = config.register(
    config.Table(
        "jobs",
        (
            config.Key(
                "jobhunt_root",
                str,
                "",
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
    """Returns the jobhunt checkout; raises `ConfigError` when `[jobs].jobhunt_root` is unset."""
    root = str(settings()["jobhunt_root"])
    if not root:
        raise config.ConfigError(
            "jobhunt_root is not set", path=paths.config_file(), table="jobs", key="jobhunt_root"
        )
    return Path(root).expanduser()
