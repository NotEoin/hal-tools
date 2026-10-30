"""Tests for command parsing, pairing, job commands and brain wiring, with fakes and no network."""

import json
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haltelegram import bridge, cli, jobs, telegram, voice
from haltelegram import settings as config
from haltelegram.acp import AcpClient

PHONE, STRANGER = 111, 999


class FakeBot:
    def __init__(self):
        self.sent, self.uploads, self.buttons = [], [], []
        self.press = None  # (chat, "allow"|"deny", nonce override) answered on the next poll
        self.updates = []

    def send(self, chat, text, buttons=None):
        self.sent.append((chat, text))
        self.buttons = buttons or self.buttons

    def typing(self, chat):
        pass

    def upload(self, method, field, path, **params):
        self.uploads.append((method, path))

    def download(self, file_id, dest):
        return dest

    def answer_callback(self, query_id, text=""):
        pass

    def call(self, method, **params):
        updates, self.updates = self.updates, []
        if self.press and self.buttons:
            chat, pick, stale = self.press
            data = next(d for label, d in self.buttons if label.lower().startswith(pick))
            if stale:
                data = data.replace(data.split(":")[2], "00000000")
            updates.append(
                {
                    "update_id": 7,
                    "callback_query": {"id": "q", "data": data, "message": {"chat": {"id": chat}}},
                }
            )
            self.press = None
        return updates


class FakeAcpAgent:
    """A scripted `hal acp` on the far end of a socketpair."""

    def __init__(self, reply="hello back", permission=None, hang=False):
        self.reply, self.permission, self.hang = reply, permission, hang
        self.prompts, self.methods, self.outcomes = [], [], []
        self.client_side, agent_side = socket.socketpair()
        self.rd, self.wr = agent_side.makefile("r"), agent_side.makefile("w")
        self.sessions = 0
        threading.Thread(target=self._serve, daemon=True).start()

    def client(self):
        return AcpClient(self.client_side.makefile("r"), self.client_side.makefile("w"))

    def _send(self, message):
        self.wr.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        self.wr.flush()

    def _serve(self):
        for line in self.rd:
            msg = json.loads(line)
            method = msg.get("method")
            self.methods.append(method)
            if method == "initialize":
                self._send({"id": msg["id"], "result": {"protocolVersion": 1}})
            elif method == "session/new":
                self.sessions += 1
                self._send({"id": msg["id"], "result": {"sessionId": f"s{self.sessions}"}})
            elif method == "session/prompt" and not self.hang:
                text = msg["params"]["prompt"][0]["text"]
                self.prompts.append(text)
                if self.permission:
                    self._send(
                        {
                            "id": 900,
                            "method": "session/request_permission",
                            "params": self.permission,
                        }
                    )
                    self.outcomes.append(json.loads(self.rd.readline())["result"]["outcome"])
                for part in (self.reply[:3], self.reply[3:]):
                    update = {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": part},
                    }
                    self._send({"method": "session/update", "params": {"update": update}})
                self._send({"id": msg["id"], "result": {"stopReason": "end_turn"}})


def broker_request(display="Run files_read with path=/x", aid="a1"):
    return {
        "_meta": {"hal/origin": "broker", "hal/approval_id": aid, "hal/display": display},
        "options": [
            {"optionId": "once", "name": "Allow once", "kind": "allow_once"},
            {"optionId": "no", "name": "Deny", "kind": "reject_once"},
        ],
    }


class FakeHub:
    def __init__(self, tools):
        self.tools, self.calls = tools, []

    def get(self, name):
        return name if name in self.tools else None

    def call(self, name, args):
        self.calls.append((name, args))
        return {"result": self.tools[name]}


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["HAL_CONFIG"] = str(Path(self.tmp.name) / "config.toml")
        self.bot = FakeBot()

    def tearDown(self):
        self.tmp.cleanup()

    def paired(self, hub=None, agent=None):
        config.write_private(config.chat_file(), str(PHONE))
        return bridge.Bridge(self.bot, agent.client if agent else None, hub)


class ParseTest(unittest.TestCase):
    def test_commands_and_text(self):
        self.assertEqual(bridge.parse("/todo  ring the agency "), ("/todo", "ring the agency"))
        self.assertEqual(bridge.parse("/Queue@HalBot"), ("/queue", ""))
        self.assertEqual(bridge.parse("what's on tomorrow?"), (None, "what's on tomorrow?"))
        self.assertEqual(bridge.parse(""), (None, ""))

    def test_token_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HAL_CONFIG"] = str(Path(tmp) / "config.toml")
            with self.assertRaises(ValueError):
                cli.save_token("not-a-token")
            cli.save_token("123456:" + "a" * 35)
            self.assertEqual(stat.S_IMODE(config.token_file().stat().st_mode), 0o600)


class PairingTest(Sandbox):
    def test_pairs_with_the_right_code_only(self):
        b = bridge.Bridge(self.bot)
        code = b.pairing_code
        self.assertRegex(code, r"^\d{6}$")
        self.assertEqual(bridge.Bridge(FakeBot()).pairing_code, code, "the code survives a restart")
        b.handle(
            {"chat": {"id": STRANGER}, "text": "/pair 000000" if code != "000000" else "/pair 1"}
        )
        self.assertIsNone(b.chat)
        self.assertIn("doesn't match", self.bot.sent[-1][1])
        b.handle({"chat": {"id": PHONE}, "text": f"/pair {code}"})
        self.assertEqual(b.chat, PHONE)
        self.assertEqual(config.chat_file().read_text(), str(PHONE))
        self.assertEqual(stat.S_IMODE(config.chat_file().stat().st_mode), 0o600)
        self.assertFalse(config.pairing_file().exists())
        self.assertTrue(self.bot.sent[-1][1].startswith("Paired."))

    def test_pairing_locks_after_five_wrong_codes(self):
        b = bridge.Bridge(self.bot)
        wrong = "/pair 1" if b.pairing_code != "1" else "/pair 2"
        with mock.patch.object(bridge.proc, "completed") as notify:
            for _ in range(5):
                b.handle({"chat": {"id": STRANGER}, "text": wrong})
            b.handle({"chat": {"id": STRANGER}, "text": f"/pair {b.pairing_code}"})
        self.assertIsNone(b.chat, "the right code is refused once locked")
        self.assertEqual(notify.call_count, 1)
        self.assertEqual(len(self.bot.sent), 4, "the fifth wrong code gets a notice, not a reply")

    def test_wrong_codes_outside_the_window_do_not_lock(self):
        b = bridge.Bridge(self.bot)
        clock = [1000.0]
        b.clock = lambda: clock[0]
        for _ in range(8):
            b.handle({"chat": {"id": STRANGER}, "text": "/pair x"})
            clock[0] += bridge.PAIRING_WINDOW_S / 3
        self.assertFalse(b.locked)

    def test_expired_code_is_replaced_and_refused(self):
        b = bridge.Bridge(self.bot)
        old = b.pairing_code
        expired = time.time() - bridge.PAIRING_TTL_S - 1
        os.utime(config.pairing_file(), (expired, expired))
        with mock.patch.object(bridge.proc, "completed"):
            b.handle({"chat": {"id": PHONE}, "text": f"/pair {old}"})
        self.assertIsNone(b.chat)
        self.assertIn("expired", self.bot.sent[-1][1])
        self.assertTrue(config.pairing_file().exists())

    def test_ignores_other_chats_once_paired(self):
        b = self.paired()
        b.handle({"chat": {"id": STRANGER}, "text": "hello"})
        self.assertEqual(self.bot.sent, [])


class AgentTest(Sandbox):
    def test_bridge_streams_acp_reply_to_chat(self):
        agent = FakeAcpAgent()
        b = self.paired(agent=agent)
        b.handle({"chat": {"id": PHONE}, "text": "add dentist"})
        b.handle({"chat": {"id": PHONE}, "text": "and remind me"})
        self.assertEqual(agent.prompts, ["add dentist", "and remind me"])
        self.assertEqual(agent.sessions, 1, "one session per chat")
        self.assertEqual(self.bot.sent[-1], (PHONE, "hello back"))

    def test_reset_starts_a_new_session(self):
        agent = FakeAcpAgent()
        b = self.paired(agent=agent)
        b.handle({"chat": {"id": PHONE}, "text": "hello"})
        b.handle({"chat": {"id": PHONE}, "text": "/reset"})
        b.handle({"chat": {"id": PHONE}, "text": "hello"})
        self.assertEqual(agent.sessions, 2)

    def test_without_an_agent_commands_still_work(self):
        self.assertIn("Hal is not available", self.paired().respond(PHONE, "hello"))

    def test_approval_buttons_carry_id_and_nonce(self):
        agent = FakeAcpAgent(permission=broker_request())
        b = self.paired(agent=agent)
        shown = []
        real = self.bot.send
        self.bot.send = lambda chat, text, buttons=None: (
            shown.append(buttons),
            real(chat, text, buttons),
        )
        self.bot.press = (PHONE, "allow", False)
        b.handle({"chat": {"id": PHONE}, "text": "read it"})
        self.assertRegex(shown[0][0][1], r"^apr:a1:[0-9a-f]{8}:allow$")
        self.assertRegex(shown[0][1][1], r"^apr:a1:[0-9a-f]{8}:deny$")
        self.assertIn("path=/x", self.bot.sent[0][1])
        self.assertEqual(agent.outcomes, [{"outcome": "selected", "optionId": "once"}])

    def test_long_request_has_no_allow_button(self):
        agent = FakeAcpAgent(permission=broker_request("x" * 4000))
        b = self.paired(agent=agent)
        self.bot.press = (PHONE, "deny", False)
        b.handle({"chat": {"id": PHONE}, "text": "go"})
        self.assertIn("Approve with: hal approve a1", self.bot.sent[0][1])
        self.assertEqual([label for label, _ in self.bot.buttons], ["Deny"])

    def test_press_from_other_chat_is_ignored(self):
        agent = FakeAcpAgent(permission=broker_request())
        b = self.paired(agent=agent)
        self.bot.press = (STRANGER, "allow", False)
        with (
            mock.patch.object(bridge, "APPROVAL_TIMEOUT_S", 0.3),
            mock.patch.object(bridge, "APPROVAL_POLL_S", 0.05),
        ):
            b.handle({"chat": {"id": PHONE}, "text": "go"})
        self.assertEqual(agent.outcomes, [{"outcome": "selected", "optionId": "no"}])

    def test_press_with_stale_nonce_is_ignored(self):
        agent = FakeAcpAgent(permission=broker_request())
        b = self.paired(agent=agent)
        self.bot.press = (PHONE, "allow", True)
        with (
            mock.patch.object(bridge, "APPROVAL_TIMEOUT_S", 0.3),
            mock.patch.object(bridge, "APPROVAL_POLL_S", 0.05),
        ):
            b.handle({"chat": {"id": PHONE}, "text": "go"})
        self.assertEqual(agent.outcomes, [{"outcome": "selected", "optionId": "no"}])

    def test_agent_originated_permission_is_cancelled(self):
        agent = FakeAcpAgent(permission={"options": [{"optionId": "once", "kind": "allow_once"}]})
        b = self.paired(agent=agent)
        b.handle({"chat": {"id": PHONE}, "text": "go"})
        self.assertEqual(agent.outcomes, [{"outcome": "cancelled"}])

    def test_turn_timeout_cancels_and_apologises(self):
        agent = FakeAcpAgent(hang=True)
        config.write_private(config.state_dir() / "config.toml", "[telegram]\nturn_timeout_s = 1\n")
        b = self.paired(agent=agent)
        b.handle({"chat": {"id": PHONE}, "text": "go"})
        self.assertEqual(self.bot.sent[-1], (PHONE, bridge.TOO_LONG))
        time.sleep(0.2)
        self.assertIn("session/cancel", agent.methods)

    def test_every_send_disables_link_previews(self):
        bot = telegram.Telegram("1:" + "a" * 35)
        with mock.patch.object(bot, "call") as call:
            bot.send(PHONE, "see https://example.test", buttons=[("Deny", "apr:a:b:deny")])
        params = call.call_args.kwargs
        self.assertEqual(json.loads(params["link_preview_options"]), {"is_disabled": True})
        self.assertIn("inline_keyboard", params["reply_markup"])

    def test_voice_note_without_whisper(self):
        b = self.paired()
        with mock.patch.object(
            voice, "transcribe", side_effect=voice.VoiceUnavailable(voice.NEEDS_VOICE)
        ):
            b.handle({"chat": {"id": PHONE}, "voice": {"file_id": "f"}})
        self.assertEqual(self.bot.sent, [(PHONE, voice.NEEDS_VOICE)])

    def test_voice_note_without_hal_voice_says_so(self):
        with mock.patch.object(voice.shutil, "which", return_value=None):
            with self.assertRaises(voice.VoiceUnavailable) as caught:
                voice.transcribe(Path("note.ogg"))
        self.assertEqual(str(caught.exception), "voice notes need hal-voice")

    def test_voice_note_is_answered_by_the_agent(self):
        b = self.paired(agent=FakeAcpAgent(reply="reply to what's the weather"))
        with (
            mock.patch.object(voice, "transcribe", return_value="what's the weather"),
            mock.patch.object(voice, "synthesise", return_value=None),
        ):
            b.handle({"chat": {"id": PHONE}, "voice": {"file_id": "f"}})
        self.assertEqual(
            self.bot.sent,
            [(PHONE, "Heard: what's the weather"), (PHONE, "reply to what's the weather")],
        )


class JobCommandTest(Sandbox):
    def test_commands_use_hub_tools(self):
        hub = FakeHub(
            {
                "jobs_queue": {
                    "ready": 1,
                    "reserve": 2,
                    "jobs": [
                        {
                            "company": "Arm",
                            "title": "Graduate Engineer",
                            "score": 71.4,
                            "location": "London",
                        }
                    ],
                },
                "jobs_mark": "ok",
                "jobs_todo": "1. reply to Arm",
                "briefing_build": "Good morning.",
            }
        )
        b = self.paired(hub)
        self.assertEqual(
            b.respond(PHONE, "/queue"), "1 ready, 2 in reserve\n71  Arm: Graduate Engineer (London)"
        )
        b.respond(PHONE, "/discard 42")
        b.respond(PHONE, "/applied 43")
        self.assertEqual(b.respond(PHONE, "/todo"), "1. reply to Arm")
        self.assertEqual(b.respond(PHONE, "/brief"), "Good morning.")
        self.assertIn(("jobs_mark", {"job": "42", "status": "skipped"}), hub.calls)
        self.assertIn(("jobs_mark", {"job": "43", "status": "applied"}), hub.calls)
        self.assertEqual(hub.calls[-1][0], "briefing_build")

    def test_former_jobhunt_commands_use_hub_tools(self):
        hub = FakeHub(
            {
                "jobs_status": "Job search: 2 need you",
                "jobs_matches": "71  Arm  arm-1",
                "jobs_shortlist": "Arm | Graduate Engineer -> shortlisted",
                "jobs_todo_add": "12  ring Arm back",
            }
        )
        b = self.paired(hub)
        self.assertEqual(b.respond(PHONE, "/status"), "Job search: 2 need you")
        self.assertEqual(b.respond(PHONE, "/jobs"), "71  Arm  arm-1")
        self.assertEqual(b.respond(PHONE, "/shortlist 7"), "Arm | Graduate Engineer -> shortlisted")
        self.assertEqual(b.respond(PHONE, "/todo ring Arm back"), "12  ring Arm back")
        self.assertEqual(
            hub.calls,
            [
                ("jobs_status", {}),
                ("jobs_matches", {}),
                ("jobs_shortlist", {"job": "7"}),
                ("jobs_todo_add", {"text": "ring Arm back"}),
            ],
        )
        self.assertFalse(hasattr(jobs, "jobhunt"), "the bridge no longer runs jobhunt itself")

    def test_pack_sends_output_and_files(self):
        pack_md, pdf = Path(self.tmp.name) / "pack.md", Path(self.tmp.name) / "cv.pdf"
        pack_md.write_text("# pack")
        pdf.write_text("%PDF")
        hub = FakeHub(
            {
                "jobs_pack": {
                    "pack": str(pack_md),
                    "output": f"7: drafting...\n  {pack_md}",
                    "files": [str(pack_md), str(pdf), str(Path(self.tmp.name) / "gone.pdf")],
                }
            }
        )
        b = self.paired(hub)
        b._pack(PHONE, "7")
        self.assertEqual(hub.calls, [("jobs_pack", {"job": "7"})])
        self.assertEqual(self.bot.sent, [(PHONE, f"7: drafting...\n  {pack_md}")])
        self.assertEqual(self.bot.uploads, [("sendDocument", pack_md), ("sendDocument", pdf)])

    def test_pack_failure_and_missing_tool(self):
        class Failing(FakeHub):
            def call(self, name, args):
                self.calls.append((name, args))
                return {"error": "RuntimeError: 2 jobs match '7'"}

        b = self.paired(Failing({"jobs_pack": None}))
        b._pack(PHONE, "7")
        self.assertEqual(
            self.bot.sent, [(PHONE, "That didn't work: RuntimeError: 2 jobs match '7'")]
        )
        self.assertEqual(self.bot.uploads, [])
        self.assertIn("hal ext add jobs", self.paired(FakeHub({})).respond(PHONE, "/pack 7"))

    def test_tool_errors_are_reported(self):
        class Failing(FakeHub):
            def call(self, name, args):
                return {"error": "RuntimeError: 0 jobs match '7'"}

        b = self.paired(Failing({"jobs_shortlist": None}))
        self.assertEqual(
            b.respond(PHONE, "/shortlist 7"), "That didn't work: RuntimeError: 0 jobs match '7'"
        )

    def test_missing_module_and_unknown_commands(self):
        b = self.paired(FakeHub({}))
        self.assertIn("hal ext add briefing", b.respond(PHONE, "/brief"))
        for command in ("/status", "/jobs", "/shortlist 7", "/todo ring Arm"):
            self.assertIn("hal ext add jobs", b.respond(PHONE, command))
        self.assertEqual(b.respond(PHONE, "/shortlist"), bridge.HELP)
        self.assertEqual(b.respond(PHONE, "/nonsense"), bridge.HELP)


if __name__ == "__main__":
    unittest.main()
