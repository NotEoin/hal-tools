"""Tests for finding, duplicates and tidying, in a throwaway folder."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halfiles import tools


class FilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "report final.pdf").write_bytes(b"%PDF" + b"x" * 2_000_000)
        (self.d / "copy of report.pdf").write_bytes(b"%PDF" + b"x" * 2_000_000)
        (self.d / "notes.md").write_text("# Notes\nhello")
        (self.d / "photo.jpg").write_bytes(b"\xff\xd8" + b"y" * 10)

    def tearDown(self):
        self.tmp.cleanup()

    def test_find_by_words_kind_and_size(self):
        self.assertEqual(len(tools.find(name="report", root=str(self.d))), 2)
        self.assertEqual(len(tools.find(kind="images", root=str(self.d))), 1)
        self.assertEqual(len(tools.find(larger_than="1mb", root=str(self.d))), 2)

    def test_duplicates(self):
        groups = tools.duplicates(str(self.d), "1mb")
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["files"]), 2)

    def test_read_markdown(self):
        self.assertIn("hello", tools.read(str(self.d / "notes.md"))["text"])

    def test_tidy_moves_by_kind(self):
        out = tools.tidy_downloads(str(self.d))
        self.assertEqual(out["moved"], {"documents": 3, "images": 1})
        self.assertTrue((self.d / "Images" / "photo.jpg").exists())


if __name__ == "__main__":
    unittest.main()
