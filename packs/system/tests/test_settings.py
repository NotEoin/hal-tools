"""Tests for the system settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from halkit.config import ConfigError
from halshell.settings import settings


class SettingsTest(unittest.TestCase):
    def _load(self, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(text)
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                return settings()

    def test_missing_file_gives_the_default_max_output(self) -> None:
        self.assertEqual(self._load("")["max_output"], 65536)

    def test_value_in_the_file_overrides_the_default(self) -> None:
        self.assertEqual(self._load("[shell]\nmax_output = 500\n")["max_output"], 500)

    def test_malformed_config_raises_with_line(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[shell]\nmax_output = \n")
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load("[shell]\nnonesuch = 1\n")
        self.assertEqual(ctx.exception.key, "nonesuch")
