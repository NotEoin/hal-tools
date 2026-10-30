"""Tests that an empty text argument falls back to the clipboard through `halhub.client.call`."""

from unittest import mock

import pytest
from halhub import client
from hallang import tools


def test_given_text_never_touches_the_hub():
    with mock.patch.object(client, "call") as call:
        assert tools._text("hello") == "hello"
    call.assert_not_called()


def test_blank_text_reads_the_clipboard_tool():
    with mock.patch.object(client, "call", return_value={"text": "copied"}) as call:
        assert tools._text("  ") == "copied"
    call.assert_called_once_with("desktop_clipboard", {}, "lang", timeout=30.0)


def test_denied_clipboard_gives_the_copy_something_first_error():
    with (
        mock.patch.object(client, "call", side_effect=client.ToolDenied("policy", "deny")),
        pytest.raises(ValueError, match="copy it to the clipboard"),
    ):
        tools._text("")
