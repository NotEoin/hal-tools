"""Tests for command parsing, pairing, job commands and the brain wiring, with fakes and no network."""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haltelegram import __main__ as cli, bridge, config, jobs, voice  # noqa: E402

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
        b.handle({"chat": {"id": STRANGER}, "text": "/pair 000000" if code != "000000" else "/pair 1"})
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
        self.assertEqual(b.brains[PHONE].asked, ["add dentist on thursday", "and remind me the day before"])
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
        self.assertIn("Core Hal isn't installed", self.paired(make_brain=None).respond(PHONE, "hello"))

    def test_voice_note_without_whisper(self):
        b = self.paired()
        with mock.patch.object(voice, "transcribe", side_effect=voice.VoiceUnavailable(voice.NEEDS_VOICE)):
            b.handle({"chat": {"id": PHONE}, "voice": {"file_id": "f"}})
        self.assertEqual(self.bot.sent, [(PHONE, voice.NEEDS_VOICE)])

    def test_voice_note_is_answered_by_the_brain(self):
        b = self.paired()
        with mock.patch.object(voice, "transcribe", return_value="what's the weather"), \
                mock.patch.object(voice, "synthesise", return_value=None):
            b.handle({"chat": {"id": PHONE}, "voice": {"file_id": "f"}})
        self.assertEqual(self.bot.sent, [(PHONE, "Heard: what's the weather"), (PHONE, "reply to what's the weather")])


class JobCommandTest(Sandbox):
    def test_commands_use_hub_tools(self):
        hub = FakeHub({"jobs_queue": {"ready": 1, "reserve": 2, "jobs": [
                           {"company": "Arm", "title": "Graduate Engineer", "score": 71.4, "location": "London"}]},
                       "jobs_mark": "ok", "jobs_todo": "1. reply to Arm", "briefing_build": "Good morning."})
        b = self.paired(hub)
        self.assertEqual(b.respond(PHONE, "/queue"), "1 ready, 2 in reserve\n71  Arm: Graduate Engineer (London)")
        b.respond(PHONE, "/discard 42")
        b.respond(PHONE, "/applied 43")
        self.assertEqual(b.respond(PHONE, "/todo"), "1. reply to Arm")
        self.assertEqual(b.respond(PHONE, "/brief"), "Good morning.")
        self.assertIn(("jobs_mark", {"job": "42", "status": "skipped"}), hub.calls)
        self.assertIn(("jobs_mark", {"job": "43", "status": "applied"}), hub.calls)
        self.assertEqual(hub.calls[-1][0], "briefing_build")

    def test_jobhunt_fallbacks(self):
        b = self.paired(FakeHub({}))
        with mock.patch.object(jobs, "jobhunt", side_effect=lambda *a, **k: " ".join(a)):
            self.assertEqual(b.respond(PHONE, "/shortlist 7"), "set 7 shortlisted")
            self.assertEqual(b.respond(PHONE, "/todo ring Arm back"), "todo add ring Arm back")
            self.assertEqual(b.respond(PHONE, "/jobs"), "list -m 60 -n 8")
            self.assertEqual(b.respond(PHONE, "/status"), "digest --dry-run")

    def test_missing_module_and_unknown_commands(self):
        b = self.paired(FakeHub({}))
        self.assertIn("hal ext add briefing", b.respond(PHONE, "/brief"))
        self.assertEqual(b.respond(PHONE, "/shortlist"), bridge.HELP)
        self.assertEqual(b.respond(PHONE, "/nonsense"), bridge.HELP)
        self.assertEqual(FakeBrain.made, 0)

    def test_jobhunt_root_from_config(self):
        config.config_path().write_text('[jobs]\njobhunt_root = "/srv/jobhunt"\n')
        self.assertEqual(config.jobhunt_root(), Path("/srv/jobhunt"))
        config.config_path().write_text('[jobs]\njobhunt = "/srv/old"\n')
        self.assertEqual(config.jobhunt_root(), Path("/srv/old"))


if __name__ == "__main__":
    unittest.main()
