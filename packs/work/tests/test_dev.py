"""Tests for hal-dev against a throwaway repository."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class DevTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        repo = Path(self.tmp.name) / "proj" / "demo"
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "a.py").write_text("x = 1  # TODO: tidy\n")
        cfg = Path(self.tmp.name) / "c.toml"
        cfg.write_text(f'[dev]\nroots = ["{Path(self.tmp.name) / "proj"}"]\n')
        os.environ["HAL_CONFIG"] = str(cfg)
        from haldev import tools

        self.tools = tools

    def tearDown(self):
        self.tmp.cleanup()

    def test_repo_found_with_changes(self):
        r = self.tools.repos()
        self.assertEqual(r[0]["repo"], "demo")
        self.assertEqual(r[0]["uncommitted"], 1)

    def test_todos_need_tracked_files(self):
        self.assertEqual(self.tools.todos("demo"), [])


if __name__ == "__main__":
    unittest.main()
