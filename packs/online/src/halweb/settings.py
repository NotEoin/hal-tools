"""Settings for halweb: the [web] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping

from halkit import config

FEEDS_DEFAULT: dict = {
    "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "Hacker News": "https://hnrss.org/frontpage",
    "The Guardian UK": "https://www.theguardian.com/uk/rss",
}

TABLE = config.register(
    config.Table(
        "web",
        (
            config.Key("home", str, "London", doc="Default place for weather and local searches"),
            config.Key("country", str, "GB", doc="ISO country code place names prefer"),
            config.Key("feeds", dict, FEEDS_DEFAULT, doc="News feeds: name to RSS URL"),
        ),
        owner="hal-online",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def shared() -> Mapping[str, object]:
    """Returns the shared `[hal]` table (models, vault, user name)."""
    return config.hal()
