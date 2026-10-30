"""Tests for the online pack's URL fetching: every fetch goes through `halkit.netguard`."""

import ast
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from hal_online import net
from halkit import netguard

SRC = Path(__file__).resolve().parents[1] / "src"
FORBIDDEN_IMPORTS = {"urllib.request", "http.client", "socket", "requests", "httpx"}


def _response(body: bytes, truncated: bool = False, status: int = 200) -> netguard.Response:
    return netguard.Response("https://x.example/", status, {}, body, truncated)


class NetguardUseTest(unittest.TestCase):
    def test_every_url_fetch_goes_through_netguard(self) -> None:
        for package in ("halweb", "halfeeds", "hal_online"):
            for path in (SRC / package).glob("*.py"):
                if (
                    path.name == "llm.py"
                ):  # the local model socket, not a URL fetch (H-19 removes it)
                    continue
                for node in ast.walk(ast.parse(path.read_text())):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        names = [f"{node.module}.{a.name}" for a in node.names] + [
                            node.module or ""
                        ]
                    self.assertFalse(
                        FORBIDDEN_IMPORTS & set(names), f"{path.name} opens its own connection"
                    )

    def test_fetch_calls_netguard_with_the_net_settings(self) -> None:
        with mock.patch.object(netguard, "fetch", return_value=_response(b"ok")) as fake:
            self.assertEqual(net.get("https://x.example/a"), b"ok")
        kwargs = fake.call_args.kwargs
        self.assertEqual(kwargs["max_bytes"], net.MAX_BYTES_DEFAULT)
        self.assertEqual(kwargs["timeout"], net.TIMEOUT_S_DEFAULT)
        self.assertEqual(kwargs["headers"]["User-Agent"], net.USER_AGENT_DEFAULT)
        self.assertNotIn("allow_http", kwargs)
        self.assertNotIn("allow_private", kwargs)

    def test_fetch_stops_at_max_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text("[net]\nmax_bytes = 1000\n")
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                with mock.patch.object(netguard, "fetch", return_value=_response(b"x")) as fake:
                    net.get("https://x.example/")
        self.assertEqual(fake.call_args.kwargs["max_bytes"], 1000)

    def test_http_error_status_raises(self) -> None:
        with mock.patch.object(netguard, "fetch", return_value=_response(b"", status=404)):
            with self.assertRaises(net.HTTPStatusError):
                net.get("https://x.example/")

    def test_feed_with_a_doctype_is_refused(self) -> None:
        bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><r>&a;</r>'
        with self.assertRaises(ET.ParseError):
            net.parse_xml(bomb)


class FeedRefreshTest(unittest.TestCase):
    def test_feed_refresh_refuses_http_feed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HAL_DATA_DIR": tmp}):
                from halfeeds import tools

                tools._db().execute(
                    "INSERT INTO feeds (url, name) VALUES ('http://plain.example/rss', 'p')"
                ).connection.commit()
                result = tools.refresh()
                self.assertEqual(result, {"new_items": 0})
                with self.assertRaises(ValueError):
                    net.get("http://plain.example/rss")


if __name__ == "__main__":
    unittest.main()
