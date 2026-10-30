"""Tests for the online settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from halkit.config import ConfigError
from halweb.settings import settings


class SettingsTest(unittest.TestCase):
    def _load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(text)
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                return settings()

    def test_missing_file_gives_the_default_feeds(self) -> None:
        self.assertIn("Hacker News", self._load("")["feeds"])

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[web]\nhome = \n")
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[web]\ncountrty = 'GB'\n")
        self.assertEqual(ctx.exception.key, "countrty")
