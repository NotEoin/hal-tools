"""Tests for spending, budgets and statement import on a throwaway store."""

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA"] = self.tmp.name
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "none.toml")
        from halledger import tools

        self.t = tools

    def tearDown(self):
        self.tmp.cleanup()

    def test_spend_categorised_against_budget(self):
        self.t.budget("eating out", "100")
        out = self.t.spend("12.50", "lunch at Pret")
        self.assertEqual(out["category"], "eating out")
        self.assertIn("12.50 of", out["budget"])

    def test_csv_import_skips_income_and_repeats(self):
        csv = Path(self.tmp.name) / "s.csv"
        today = date.today().strftime("%d/%m/%Y")
        csv.write_text(
            f"Date,Description,Amount\n{today},TESCO STORES,-23.10\n{today},SALARY,2000\n"
        )
        self.assertEqual(self.t.import_csv(str(csv))["imported"], 1)
        self.assertEqual(self.t.import_csv(str(csv))["imported"], 0)
        self.assertEqual(self.t.summary()["categories"][0]["category"], "groceries")


if __name__ == "__main__":
    unittest.main()
