"""Smoke test: the models tools answer when Ollama is running."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

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

    def test_gpu_lists_program_names_without_command_lines(self):
        answers = iter(["RTX, 1000, 8000, 5, 40", "4242, /usr/bin/python3, 512"])

        def fake(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, next(answers), "")

        with mock.patch.object(tools.proc, "completed", fake):
            out = tools.gpu()
        self.assertEqual(out["programs"], [{"pid": 4242, "program": "python3", "memory_mb": 512}])


if __name__ == "__main__":
    unittest.main()
