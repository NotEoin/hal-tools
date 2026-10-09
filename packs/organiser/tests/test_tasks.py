"""Tests for adding, completing, repeats and the vault mirror, on a throwaway store and vault."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TasksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "vault").mkdir()
        (base / "c.toml").write_text(f'[hal]\nvault = "{base / "vault"}"\n')
        os.environ["HAL_CONFIG"] = str(base / "c.toml")
        os.environ["HAL_DATA"] = str(base / "data")
        from haltasks import tools
        self.t = tools
        self.note = base / "vault" / "Tasks.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_due_date_read_from_title(self):
        added = self.t.add("Buy milk tomorrow")["added"]
        self.assertEqual(added["title"], "Buy milk")
        self.assertIsNotNone(added["due"])

    def test_repeating_task_reschedules(self):
        self.t.add("Water plants", due="every monday at 9")
        out = self.t.done("plants")
        self.assertIn("next", out)
        self.assertEqual(self.t.list_tasks()["count"], 1)

    def test_ticking_in_the_vault_completes_the_task(self):
        self.t.add("Call the bank", project="Admin")
        text = self.note.read_text()
        self.assertIn("## [[Admin]]", text)
        self.note.write_text(text.replace("- [ ] Call the bank", "- [x] Call the bank"))
        self.assertEqual(self.t.list_tasks()["count"], 0)

    def test_unknown_task_is_an_error(self):
        with self.assertRaises(ValueError):
            self.t.done("nothing like this")


if __name__ == "__main__":
    unittest.main()
