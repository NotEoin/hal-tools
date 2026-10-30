"""Tests for hal-phone's checks that need no phone."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halphone import tools


class PhoneTest(unittest.TestCase):
    def test_bad_number_refused(self):
        with self.assertRaises(ValueError):
            tools.sms("call me maybe", "hi")

    def test_missing_kde_connect_explains_setup(self):
        if tools.shutil.which("kdeconnect-cli"):
            self.skipTest("KDE Connect is installed")
        with self.assertRaises(RuntimeError) as e:
            tools.devices()
        self.assertIn("apt install kdeconnect", str(e.exception))


if __name__ == "__main__":
    unittest.main()
