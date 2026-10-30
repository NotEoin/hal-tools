"""Settings for halledger: the [ledger] table of the shared config, read through `halkit.config`.

A malformed file or an unknown key raises `ConfigError` (REQ-PACK-12); nothing is swallowed.
"""

from collections.abc import Mapping
from pathlib import Path

from halkit import config, paths

CATEGORIES_DEFAULT: dict = {
    "groceries": [
        "tesco",
        "sainsbury",
        "asda",
        "aldi",
        "lidl",
        "waitrose",
        "co-op",
        "morrisons",
        "groceries",
        "m&s food",
    ],
    "eating out": [
        "lunch",
        "dinner",
        "restaurant",
        "pret",
        "nando",
        "deliveroo",
        "uber eats",
        "just eat",
        "cafe",
        "coffee",
        "costa",
        "starbucks",
        "greggs",
        "pub",
        "takeaway",
    ],
    "transport": [
        "tfl",
        "uber",
        "train",
        "bus",
        "trainline",
        "lner",
        "petrol",
        "fuel",
        "parking",
        "oyster",
        "metro",
    ],
    "bills": [
        "rent",
        "council tax",
        "electric",
        "gas",
        "water",
        "broadband",
        "phone bill",
        "energy",
        "insurance",
    ],
    "subscriptions": [
        "netflix",
        "spotify",
        "prime",
        "disney",
        "youtube",
        "apple.com",
        "icloud",
        "github",
        "chatgpt",
    ],
    "shopping": ["amazon", "ebay", "argos", "currys", "ikea", "clothes", "asos", "primark"],
    "health": ["pharmacy", "boots", "superdrug", "dentist", "gym", "prescription"],
    "entertainment": ["cinema", "steam", "concert", "tickets", "game"],
}

TABLE = config.register(
    config.Table(
        "ledger",
        (
            config.Key("symbol", str, "\u00a3", doc="Currency symbol shown before amounts"),
            config.Key(
                "categories",
                dict,
                CATEGORIES_DEFAULT,
                doc="Category name to keywords matched in a spend description",
            ),
        ),
        owner="hal-life",
    )
)


def settings() -> Mapping[str, object]:
    """Returns this module's validated settings; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def data_dir() -> Path:
    """Returns this module's data directory, creating it."""
    path = paths.data_dir() / "ledger"
    path.mkdir(parents=True, exist_ok=True)
    return path
