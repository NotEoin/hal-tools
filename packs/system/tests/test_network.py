"""Tests for the network tools that need no internet."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halnet import tools


class NetworkTest(unittest.TestCase):
    @pytest.mark.host  # talks to the real NetworkManager and loopback
    def test_status_lists_devices(self):
        self.assertIn("devices", tools.status())

    @pytest.mark.host  # talks to the real NetworkManager and loopback
    def test_port_checks_stay_local(self):
        with self.assertRaises(ValueError):
            tools.port("8.8.8.8", 53)
        self.assertIn("open", tools.port("127.0.0.1", 1))


if __name__ == "__main__":
    unittest.main()
