"""Tests for contacts on a throwaway vault, with calendar calls switched off."""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ContactsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Path(self.tmp.name) / "c.toml"
        cfg.write_text(f'[hal]\nvault = "{self.tmp.name}"\n')
        os.environ["HAL_CONFIG"] = str(cfg)
        from halcontacts import tools

        tools._hub = lambda *a, **k: None
        self.t = tools

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_get_and_log(self):
        self.t.add("Sam Lee", email="sam@example.com", relationship="friend from uni")
        self.t.log("sam", "lunch, talked about Leeds")
        got = self.t.get("Sam Lee")
        self.assertEqual(got["email"], "sam@example.com")
        self.assertEqual(got["last_contact"], date.today().isoformat())
        self.assertIn("talked about Leeds", got["notes"])

    def test_birthdays_ahead(self):
        soon = date.today() + timedelta(days=3)
        self.t.add("Ana", birthday=f"{soon.year - 30}-{soon:%m-%d}")
        self.assertEqual(self.t.birthdays(7)[0]["turning"], 30)

    def test_vcard_import(self):
        vcf = Path(self.tmp.name) / "c.vcf"
        vcf.write_text("BEGIN:VCARD\nFN:Jo Bloggs\nTEL:0123\nBDAY:--0704\nEND:VCARD\n")
        self.assertEqual(self.t.import_vcard(str(vcf))["imported"], 1)
        self.assertEqual(self.t.get("Jo")["birthday"], "07-04")


if __name__ == "__main__":
    unittest.main()
