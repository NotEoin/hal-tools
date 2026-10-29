"""Smoke tests for the device listings."""
import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haldevices import tools  # noqa: E402


class DevicesTest(unittest.TestCase):
    @pytest.mark.host  # lists the real USB and monitor devices
    def test_listings(self):
        self.assertIsInstance(tools.usb(), list)
        self.assertIsInstance(tools.monitors(), list)
        self.assertTrue(all("hub" not in u.lower() for u in tools.usb()))

    def test_printing_a_missing_file(self):
        with self.assertRaises(ValueError):
            tools.print_file("/no/such/file.pdf")


if __name__ == "__main__":
    unittest.main()
