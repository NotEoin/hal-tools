"""Tests for the organiser settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path

from halcal.settings import settings as calendar_settings
from halkit.config import ConfigError
from halnotify.settings import settings as notify_settings


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
        self.assertEqual(calendar_settings()["sync_minutes"], 15)

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        self.cfg.write_text("[calendar]\nsync_minutes = \n")
        with self.assertRaises(ConfigError) as ctx:
            calendar_settings()
        self.assertIn(str(self.cfg), str(ctx.exception))
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        self.cfg.write_text("[notify]\nquiet_form = 22\n")
        with self.assertRaises(ConfigError) as ctx:
            notify_settings()
        self.assertEqual(ctx.exception.key, "quiet_form")

    def test_file_value_overrides_the_default(self) -> None:
        self.cfg.write_text("[notify]\nquiet_from = 23\n")
        self.assertEqual(notify_settings()["quiet_from"], 23)
