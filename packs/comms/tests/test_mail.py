"""Offline tests for header decoding and body extraction."""
import email
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halmail import tools  # noqa: E402


class MailTest(unittest.TestCase):
    def test_encoded_and_folded_headers(self):
        self.assertEqual(tools._decode("=?utf-8?q?Caf=C3=A9_menu?=\r\n soon"), "Café menu soon")

    def test_html_body_becomes_text(self):
        msg = email.message_from_string(
            "Content-Type: text/html\n\n<html><style>p{}</style><p>Hello <b>Dave</b></p></html>")
        self.assertEqual(tools._body(msg), "Hello Dave")

    def test_unknown_account(self):
        with self.assertRaises(ValueError):
            tools._account("nope")


if __name__ == "__main__":
    unittest.main()
