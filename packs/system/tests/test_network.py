"""Tests for the network tools that need no internet."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halnet import tools  # noqa: E402


class NetworkTest(unittest.TestCase):
    def test_status_lists_devices(self):
        self.assertIn("devices", tools.status())

    def test_port_checks_stay_local(self):
        with self.assertRaises(ValueError):
            tools.port("8.8.8.8", 53)
        self.assertIn("open", tools.port("127.0.0.1", 1))


if __name__ == "__main__":
    unittest.main()
