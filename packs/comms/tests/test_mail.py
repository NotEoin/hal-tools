"""Offline tests for header decoding and body extraction."""

import email
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halmail import tools


class MailTest(unittest.TestCase):
    def test_encoded_and_folded_headers(self):
        self.assertEqual(
            tools._decode("=?utf-8?q?Caf=C3=A9_menu?=\r\n soon"), "Caf\u00e9 menu soon"
        )

    def test_html_body_becomes_text(self):
        msg = email.message_from_string(
            "Content-Type: text/html\n\n<html><style>p{}</style><p>Hello <b>Dave</b></p></html>"
        )
        self.assertEqual(tools._body(msg), "Hello Dave")

    def _config(self, text: str) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cfg = Path(tmp.name) / "config.toml"
        cfg.write_text(text)
        pw = Path(tmp.name) / "pw"
        pw.write_text("app pass")
        old = os.environ.get("HAL_CONFIG")
        os.environ["HAL_CONFIG"] = str(cfg)
        self.addCleanup(
            lambda: (
                os.environ.__setitem__("HAL_CONFIG", old)
                if old is not None
                else os.environ.pop("HAL_CONFIG", None)
            )
        )
        self.pw = pw

    def test_mail_without_accounts_fails_with_setup_message(self):
        self._config("")
        for call in (tools.accounts, tools.unread, lambda: tools.search("x")):
            with self.assertRaisesRegex(ValueError, r"no mail account configured: add \[mail"):
                call()

    def test_unknown_account(self):
        self._config("")
        with self.assertRaises(ValueError):
            tools._account("nope")

    def test_single_account_is_used_without_a_default(self):
        self._config("[mail.accounts.me]\naddress='a@example.com'\n")
        cfg = Path(os.environ["HAL_CONFIG"])
        cfg.write_text(
            f"[mail.accounts.me]\naddress='a@example.com'\nimap='i'\nsmtp='s'\n"
            f"password_file='{self.pw}'\n"
        )
        self.assertEqual(tools._account()["password"], "apppass")

    def test_search_word_quotes_and_backslashes_are_escaped(self):
        # a quote in a word used to end the IMAP string early and inject search keys
        self.assertEqual(tools._quote('a" OR ALL'), '"a\\" OR ALL"')
        self.assertEqual(tools._quote("a\\b"), '"a\\\\b"')


if __name__ == "__main__":
    unittest.main()
