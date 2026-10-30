"""Tests that briefing parts come from `halhub.client.call` and a denial only drops the part."""

from unittest import mock

from halbrief import tools
from halhub import client


def test_hub_part_is_fetched_with_the_briefing_caller_and_a_timeout():
    with mock.patch.object(client, "call", return_value={"ok": 1}) as call:
        assert tools._hub("web_weather", days=2) == {"ok": 1}
    call.assert_called_once_with("web_weather", {"days": 2}, "briefing", timeout=120.0)


def test_denied_part_is_left_out_instead_of_failing_the_briefing():
    with mock.patch.object(client, "call", side_effect=client.ToolDenied("policy", "ask")):
        assert tools._hub("tasks_list") is None


def test_failed_part_is_left_out_instead_of_failing_the_briefing():
    with mock.patch.object(client, "call", side_effect=client.ToolFailed("error", "boom")):
        assert tools._hub("tasks_list") is None
