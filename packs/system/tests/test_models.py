"""Smoke test: the models tools answer when Ollama is running."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halmodels import tools


class ModelsTest(unittest.TestCase):
    @pytest.mark.host  # needs a running Ollama
    def test_installed_is_a_list(self):
        try:
            self.assertIsInstance(tools.installed(), list)
        except OSError:
            self.skipTest("Ollama is not running")


if __name__ == "__main__":
    unittest.main()
