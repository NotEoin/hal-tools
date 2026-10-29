"""Tests for the package tools that change nothing."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halpkgs import tools  # noqa: E402


class PackagesTest(unittest.TestCase):
    @pytest.mark.host  # queries the real package manager
    def test_installed_check(self):
        self.assertTrue(tools.is_installed("bash")["apt"])

    def test_install_refuses_odd_names(self):
        for bad in ("vim; rm -rf ~", "../x", ""):
            with self.assertRaises(ValueError):
                tools.install(bad)


if __name__ == "__main__":
    unittest.main()
