"""Tests for the work settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from haldev.settings import roots, settings
from halkit.config import ConfigError


class SettingsTest(unittest.TestCase):
    def _load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(text)
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                return settings()

    def test_missing_file_gives_the_default_depth(self) -> None:
        self.assertEqual(self._load("")["depth"], 2)

    def test_default_roots_are_personal_free_and_only_existing_ones_count(self) -> None:
        self.assertEqual(self._load("")["roots"], ["~/src", "~/projects"])
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(f'[dev]\nroots = ["{tmp}", "{tmp}/missing"]\n')
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                self.assertEqual(roots(), [Path(tmp)])

    def test_value_in_the_file_overrides_the_default(self) -> None:
        self.assertEqual(self._load("[dev]\ndepth = 3\n")["depth"], 3)

    def test_malformed_config_raises_with_line(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[dev]\ndepth = \n")
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[dev]\nnonesuch = 1\n")
        self.assertEqual(ctx.exception.key, "nonesuch")
