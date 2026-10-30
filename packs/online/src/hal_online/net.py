"""The online pack's one way to fetch a URL: `halkit.netguard` plus the shared `[net]` table.

Every model-chosen or feed-supplied URL goes through here (REQ-PACK-18). Scheme, address and
redirect rules come from `policy.toml` `[egress]`; this module adds only the read cap, the
timeout and the user agent, so a pack setting can narrow the rules and never widen them.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from collections.abc import Mapping

from halkit import config, netguard

log = logging.getLogger(__name__)

MAX_BYTES_DEFAULT = 2_000_000  # a page or feed above 2 MB is no use to a model
TIMEOUT_S_DEFAULT = 20.0  # the feed fetch timeout before the netguard port
USER_AGENT_DEFAULT = "Hal/0.1 (+https://github.com/NotEoin/hal-tools)"

TABLE = config.register(
    config.Table(
        "net",
        (
            config.Key("max_bytes", int, MAX_BYTES_DEFAULT, doc="Largest page or feed read"),
            config.Key("timeout_s", float, TIMEOUT_S_DEFAULT, doc="Seconds before a fetch fails"),
            config.Key("user_agent", str, USER_AGENT_DEFAULT, doc="User-Agent header sent"),
        ),
        owner="hal-online",
    )
)


class HTTPStatusError(OSError):
    """The server answered with a status outside 200-299."""


def settings() -> Mapping[str, object]:
    """Returns the validated `[net]` table; raises `ConfigError` on a bad config file."""
    return config.load(TABLE)


def fetch(url: str, headers: Mapping[str, str] | None = None) -> netguard.Response:
    """Fetches `url` under the egress rules; `HTTPStatusError` on a status outside 200-299."""
    cfg = settings()
    sent = {"User-Agent": str(cfg["user_agent"]), "Accept-Language": "en-GB,en"}
    sent.update(headers or {})
    response = netguard.fetch(
        url,
        domains=(),
        timeout=float(cfg["timeout_s"]),
        max_bytes=int(cfg["max_bytes"]),
        headers=sent,
    )
    if not 200 <= response.status < 300:
        raise HTTPStatusError(f"{url} answered HTTP {response.status}")
    if response.truncated:
        log.warning("%s was cut at %s bytes", url, cfg["max_bytes"])
    return response


def get(url: str) -> bytes:
    """The body of `url`, cut at `[net].max_bytes`."""
    return fetch(url).body


def parse_xml(data: bytes) -> ET.Element:
    """Parses a feed; refuses a DOCTYPE, which is how entity-expansion bombs are declared."""
    head = data[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise ET.ParseError("feeds with a DOCTYPE or entity declaration are refused")
    return ET.fromstring(data)  # noqa: S314 - DOCTYPE refused above, size capped by `[net].max_bytes`
