"""Tests for subscriptions and unread tracking, using a feed file on disk."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FeedsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_DATA_DIR"] = self.tmp.name
        self.feed = (
            b"<rss><channel><title>Blog</title><item><title>First post</title>"
            b"<link>https://x.example/1</link>"
            b"<description>&lt;p&gt;Hello&lt;/p&gt;</description></item></channel></rss>"
        )
        self.url = "https://x.example/feed.xml"
        from halfeeds import tools

        self.t = tools
        patch = mock.patch.object(tools, "_get", side_effect=lambda url: self.feed)
        patch.start()
        self.addCleanup(patch.stop)

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
