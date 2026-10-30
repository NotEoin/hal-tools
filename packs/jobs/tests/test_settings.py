"""Tests for the jobs settings table: it loads through `halkit.config` and fails loudly."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from haljobs import settings as jobs_settings
from haljobs.settings import settings
from halkit.config import ConfigError


class SettingsTest(unittest.TestCase):
    def _load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(text)
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                return settings(), str(cfg)

    def test_legacy_jobhunt_key_is_accepted(self) -> None:
        loaded, _ = self._load('[jobs]\njobhunt = "/srv/jh"\n')
        self.assertEqual(loaded["jobhunt_root"], "/srv/jh")

    def test_absent_jobs_table_warns_once_and_keeps_the_old_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text("")
            with (
                mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}),
                mock.patch.object(jobs_settings, "_warned", False),
                self.assertLogs("hal-jobs", "WARNING") as logs,
            ):
                first = jobs_settings.jobhunt_root()
                jobs_settings.jobhunt_root()
        self.assertEqual(first.name, "employment-helper")
        self.assertEqual(len(logs.records), 1)

    def test_present_jobs_table_does_not_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text('[jobs]\njobhunt_root = "/srv/jh"\n')
            with (
                mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}),
                mock.patch.object(jobs_settings, "_warned", False),
                self.assertNoLogs("hal-jobs", "WARNING"),
            ):
                self.assertEqual(jobs_settings.jobhunt_root(), Path("/srv/jh"))

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[jobs]\nemployment_url = \n")
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[jobs]\nbogus = 1\n")
        self.assertEqual(ctx.exception.key, "bogus")
