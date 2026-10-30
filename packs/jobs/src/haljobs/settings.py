"""Settings for haljobs: the [jobs] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

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
