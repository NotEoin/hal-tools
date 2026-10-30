"""Tests for `hallang` text tools: they reach the model only through `halkit.llm`."""

import unittest
from unittest import mock

from hallang import tools


class LangModelTest(unittest.TestCase):
    def test_text_is_used_when_given(self) -> None:
        self.assertEqual(tools._text("hello"), "hello")

    def test_translate_sends_system_and_user_messages_to_the_gateway_client(self) -> None:
        with mock.patch.object(tools.halkit_llm, "chat", return_value=" Bonjour ") as fake:
            out = tools.translate(text="Hello", to="French")
        self.assertEqual(out, {"to": "French", "translation": "Bonjour"})
        messages = fake.call_args.args[0]
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertEqual(messages[1]["content"], "Hello")
        self.assertEqual(fake.call_args.kwargs["timeout"], tools.MODEL_TIMEOUT_S)

    def test_proofread_reply_that_is_not_json_gives_an_empty_result(self) -> None:
        with mock.patch.object(tools.halkit_llm, "chat", return_value="not json"):
            out = tools.proofread(text="Helo")
        self.assertEqual(out, {"corrected": "", "changes": []})


if __name__ == "__main__":
    unittest.main()
