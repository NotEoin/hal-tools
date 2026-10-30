"""Tests for the comms settings tables: they load through `halkit.config` and fail loudly."""

import os
import tempfile
import unittest
from pathlib import Path

from halkit.config import ConfigError
from halmail.settings import settings as mail_settings
from haltelegram.settings import settings as telegram_settings


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
        self.assertTrue(telegram_settings()["voice_replies"])

    def test_malformed_config_raises_with_path_and_line(self) -> None:
        self.cfg.write_text("[mail]\ndefault = \n")
        with self.assertRaises(ConfigError) as ctx:
            mail_settings()
        self.assertIn(str(self.cfg), str(ctx.exception))
        self.assertEqual(ctx.exception.line, 2)

    def test_unknown_key_raises_naming_the_key(self) -> None:
        self.cfg.write_text("[telegram]\nwisper_replies = 'x'\n")
        with self.assertRaises(ConfigError) as ctx:
            telegram_settings()
        self.assertEqual(ctx.exception.key, "wisper_replies")

    def test_turn_timeout_of_the_wrong_type_is_rejected(self) -> None:
        self.cfg.write_text("[telegram]\nturn_timeout_s = 'soon'\n")
        with self.assertRaises(ConfigError):
            telegram_settings()
