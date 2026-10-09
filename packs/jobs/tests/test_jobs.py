"""Tests for hal-jobs' checks that need no job data."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haljobs import tools  # noqa: E402


class JobsTest(unittest.TestCase):
    def test_unknown_status_is_refused(self):
        with self.assertRaises(ValueError):
            tools.mark("any", "hired-yesterday")


if __name__ == "__main__":
    unittest.main()
