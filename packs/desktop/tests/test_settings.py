"""Tests for the desktop settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path

from halkit.config import ConfigError
from halmedia.settings import settings as media_settings
from halrgb.settings import settings as rgb_settings


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Path(self.tmp.name) / "config.toml"
        self.old = os.environ.get("HAL_CONFIG")
        os.environ["HAL_CONFIG"] = str(self.cfg)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self.old is None:
            os.environ.pop("HAL_CONFIG", None)
        else:
            os.environ["HAL_CONFIG"] = self.old

    def test_missing_file_gives_the_defaults(self) -> None:
        self.assertEqual(rgb_settings()["port"], 6742)

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        self.cfg.write_text("[rgb]\nport = \n")
        with self.assertRaises(ConfigError) as ctx:
            rgb_settings()
        self.assertIn(str(self.cfg), str(ctx.exception))
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        self.cfg.write_text("[media]\nplayr = 'x'\n")
        with self.assertRaises(ConfigError) as ctx:
            media_settings()
        self.assertEqual(ctx.exception.key, "playr")

    def test_wrong_type_is_rejected(self) -> None:
        self.cfg.write_text("[rgb]\nport = 'abc'\n")
        with self.assertRaises(ConfigError):
            rgb_settings()
