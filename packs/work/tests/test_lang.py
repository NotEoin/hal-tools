"""Tests for hal-lang that need no model."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hallang import tools  # noqa: E402


class LangTest(unittest.TestCase):
    def test_text_is_used_when_given(self):
        self.assertEqual(tools._text("hello"), "hello")


if __name__ == "__main__":
    unittest.main()
