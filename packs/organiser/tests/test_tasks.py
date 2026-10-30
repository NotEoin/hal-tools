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
        os.environ["HAL_DATA_DIR"] = str(base / "data")
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

    def test_due_time_with_a_part_of_the_day(self):
        self.assertEqual(
            self.t.add("Call mum", due="7 tomorrow morning")["added"]["due"][11:], "07:00"
        )
        self.assertEqual(
            self.t.add("Put the bins out", due="tonight at 8")["added"]["due"][11:], "20:00"
        )

    def test_done_from_the_users_own_words(self):
        self.t.add("Buy batteries")
        self.t.add("Email the landlord")
        for said in (
            "bought the batteries",
            "I've bought the batteries, tick that off",
            "batteries",
            "buy battery",
        ):
            self.assertEqual(self.t.done(said)["done"], "Buy batteries", said)
            self.t.undo("Buy batteries")
        self.assertEqual(self.t.done("emailed my landlord")["done"], "Email the landlord")

    def test_an_open_task_wins_over_a_done_one_with_the_same_title(self):
        self.t.add("Buy batteries")
        self.t.done("bought the batteries")
        self.t.add("Buy batteries")
        self.assertEqual(self.t.done("bought the batteries")["done"], "Buy batteries")
        self.assertEqual(self.t.list_tasks()["count"], 0)
        self.assertEqual(self.t.undo("batteries")["reopened"], "Buy batteries")

    def test_ids_are_exact(self):
        first = self.t.add("Water plants")["added"]["id"]
        self.t.add("Water the garden")
        for said in (str(first), f"#{first}", f"task {first}"):
            self.assertEqual(self.t.done(said)["done"], "Water plants")
            self.t.undo(str(first))

    def test_ambiguous_words_list_the_candidates(self):
        self.t.add("Water plants")
        self.t.add("Water the garden")
        with self.assertRaises(ValueError) as err:
            self.t.done("watering")
        self.assertIn("Water plants", str(err.exception))
        self.assertIn("Water the garden", str(err.exception))
        self.assertEqual(self.t.list_tasks()["count"], 2)

    def test_edit_delete_and_undo_use_the_same_matching(self):
        self.t.add("Renew passport")
        self.t.add("Book dentist")
        self.assertEqual(
            self.t.edit("renewing my passport", priority="high")["edited"]["priority"], "high"
        )
        self.t.done("renewed the passport")
        self.t.add("Renew car insurance")
        self.assertEqual(self.t.undo("the passport")["reopened"], "Renew passport")
        self.assertEqual(self.t.delete("booking the dentist")["deleted"], "Book dentist")

    def test_dates_in_the_words_are_ignored(self):
        self.t.add("Call the bank", due="friday")
        self.assertEqual(self.t.done("called the bank on friday")["done"], "Call the bank")

    def test_stems(self):
        from haltasks.match import stem

        for a, b in [
            ("bought", "buy"),
            ("batteries", "battery"),
            ("ticking", "tick"),
            ("shopping", "shop"),
            ("called", "call"),
            ("made", "make"),
            ("running", "run"),
            ("adding", "add"),
        ]:
            self.assertEqual(stem(a), stem(b), (a, b))


if __name__ == "__main__":
    unittest.main()
