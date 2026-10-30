"""Tests for subscriptions and unread tracking, using a feed file on disk."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FeedsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        feed = Path(self.tmp.name) / "f.xml"
        feed.write_text(
            "<rss><channel><title>Blog</title><item><title>First post</title><link>http://x/1</link>"
            "<description>&lt;p&gt;Hello&lt;/p&gt;</description></item></channel></rss>"
        )
        self.url = feed.as_uri()
        from halfeeds import tools

        self.t = tools

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_items_then_read(self):
        self.t.subscribe(self.url)
        new = self.t.whats_new()
        self.assertEqual(new[0]["title"], "First post")
        self.assertEqual(new[0]["summary"], "Hello")
        self.t.mark_read("First post")
        self.assertEqual(self.t.whats_new(), [])


if __name__ == "__main__":
    unittest.main()
