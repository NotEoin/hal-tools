"""Tests for hal-screen that need no screen or model."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halscreen import tools


class ScreenTest(unittest.TestCase):
    def test_missing_image_is_an_error(self):
        with self.assertRaises(ValueError):
            tools.describe_image("/no/such/image.png")


if __name__ == "__main__":
    unittest.main()
