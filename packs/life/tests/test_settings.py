"""Tests for the life settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from halcontacts.settings import settings as contacts_settings
from halkit.config import ConfigError
from halledger.settings import settings as ledger_settings


class SettingsTest(unittest.TestCase):
    def _load(self, loader, text: str):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.toml"
            cfg.write_text(text)
            with mock.patch.dict(os.environ, {"HAL_CONFIG": str(cfg)}):
                return loader()

    def test_ledger_symbol_defaults_to_the_pound_sign(self) -> None:
        self.assertEqual(self._load(ledger_settings, "")["symbol"], "\u00a3")

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load(contacts_settings, "[contacts]\nfolder = \n")
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        with self.assertRaises(ConfigError) as ctx:
            self._load(ledger_settings, "[ledger]\nsymbl = 'x'\n")
        self.assertEqual(ctx.exception.key, "symbl")
