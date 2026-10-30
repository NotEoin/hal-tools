"""Smoke tests: every read-only tool answers on this machine with the expected shape."""

import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halsys import tools


class SystemTest(unittest.TestCase):
    @pytest.mark.host  # needs the real /proc and disks
    def test_overview(self):
        o = tools.overview()
        self.assertGreater(o["memory"]["total_gb"], 0)
        self.assertGreaterEqual(o["cpu"]["use_percent"], 0)

    @pytest.mark.host  # needs the real /proc and disks
    def test_disks_include_root(self):
        self.assertIn("/", [d["mount"] for d in tools.disks()])

    @pytest.mark.host  # needs the real /proc and disks
    def test_processes_sorted_and_limited(self):
        procs = tools.processes("memory", 5)
        self.assertLessEqual(len(procs), 5)
        self.assertEqual(procs, sorted(procs, key=lambda p: -p["memory_percent"]))

    def test_kill_refuses_unknown_names(self):
        with self.assertRaises(ValueError):
            tools.kill("no-such-process-name-xyz")


if __name__ == "__main__":
    unittest.main()
