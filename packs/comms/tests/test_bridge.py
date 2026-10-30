"""Tests for command parsing, pairing, job commands and the brain wiring, with fakes and no network."""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haltelegram import __main__ as cli
from haltelegram import bridge, jobs, voice
from haltelegram import settings as config

PHONE, STRANGER = 111, 999


class FakeBot:
    def __init__(self):
        self.sent, self.uploads = [], []

    def send(self, chat, text):
        self.sent.append((chat, text))

    def typing(self, chat):
        pass

    def upload(self, method, field, path, **params):
        self.uploads.append((method, path))

    def download(self, file_id, dest):
        return dest


class FakeBrain:
    made = 0

    def __init__(self):
        FakeBrain.made += 1
        self.asked, self.resets, self.on_deep_done = [], 0, None

    def reply(self, text):
        self.asked.append(text)
        return f"reply to {text}"

    def reset(self):
        self.resets += 1


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
        FakeBrain.made = 0
        self.bot = FakeBot()

    def tearDown(self):
        self.tmp.cleanup()

    def paired(self, hub=None, make_brain=FakeBrain):
        config.write_private(config.chat_file(), str(PHONE))
        return bridge.Bridge(self.bot, make_brain, hub)


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

    def test_ignores_other_chats_once_paired(self):
        b = self.paired()
        b.handle({"chat": {"id": STRANGER}, "text": "hello"})
        self.assertEqual(self.bot.sent, [])
        self.assertEqual(FakeBrain.made, 0)


class BrainTest(Sandbox):
    def test_free_text_goes_to_one_brain_per_chat(self):
        b = self.paired()
        b.handle({"chat": {"id": PHONE}, "text": "add dentist on thursday"})
        b.handle({"chat": {"id": PHONE}, "text": "and remind me the day before"})
        self.assertEqual(FakeBrain.made, 1)
        self.assertEqual(
            b.brains[PHONE].asked, ["add dentist on thursday", "and remind me the day before"]
        )
        self.assertEqual(self.bot.sent[-1], (PHONE, "reply to and remind me the day before"))
        self.assertIsNot(b.brain_for(STRANGER), b.brains[PHONE])

    def test_reset_clears_the_conversation(self):
        b = self.paired()
        b.handle({"chat": {"id": PHONE}, "text": "hello"})
        b.handle({"chat": {"id": PHONE}, "text": "/reset"})
        self.assertEqual(b.brains[PHONE].resets, 1)

    def test_background_work_is_reported(self):
        b = self.paired()
        b.brain_for(PHONE).on_deep_done("the report is written")
        self.assertEqual(self.bot.sent[-1][0], PHONE)
        self.assertIn("the report is written", self.bot.sent[-1][1])

    def test_model_down_falls_back_to_commands(self):
        class Down(FakeBrain):
            def reply(self, text):
                raise OSError("connection refused")

        b = self.paired(make_brain=Down)
        self.assertEqual(b.respond(PHONE, "hello"), bridge.NO_MODEL)
        self.assertIn(
            "Core Hal isn't installed", self.paired(make_brain=None).respond(PHONE, "hello")
        )

    def test_voice_note_without_whisper(self):
        b = self.paired()
        with mock.patch.object(
            voice, "transcribe", side_effect=voice.VoiceUnavailable(voice.NEEDS_VOICE)
        ):
            b.handle({"chat": {"id": PHONE}, "voice": {"file_id": "f"}})
        self.assertEqual(self.bot.sent, [(PHONE, voice.NEEDS_VOICE)])

    def test_voice_note_is_answered_by_the_brain(self):
        b = self.paired()
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
        self.assertEqual(FakeBrain.made, 0)


if __name__ == "__main__":
    unittest.main()
