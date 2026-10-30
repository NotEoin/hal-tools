"""Tests that a birthday event goes to the calendar through `halhub.client.call`."""

from unittest import mock

from halcontacts import tools
from halhub import client


def test_calendar_call_uses_the_contacts_caller_and_a_timeout():
    with mock.patch.object(client, "call") as call:
        tools._hub("calendar_add", {"title": "x"})
    call.assert_called_once_with("calendar_add", {"title": "x"}, "contacts", timeout=60.0)


def test_denied_calendar_call_is_logged_and_does_not_raise():
    with mock.patch.object(client, "call", side_effect=client.ToolDenied("policy", "deny")):
        tools._hub("calendar_add", {"title": "x"})
