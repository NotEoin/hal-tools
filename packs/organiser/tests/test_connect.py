"""Tests for `python3 -m halcal connect` and setup_caldav, with a fake CalDAV client (no network)."""
import os
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CALENDARS = [{"name": "Shared family", "href": "/1/family/", "writable": False},
             {"name": "Home", "href": "/1/home/", "writable": True},
             {"name": "Work", "href": "/1/work/", "writable": True}]


class FakeClient:
    made = []

    def __init__(self, url, username, password):
        FakeClient.made.append((url, username, password))
        self.password = password

    def calendars(self):
        from halcal.caldav import CalDAVError
        if self.password != "good-pass":
            raise CalDAVError("the server refused the username or app-specific password")
        return CALENDARS


class ConnectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.cfg = base / "config" / "config.toml"
        self.cfg.parent.mkdir()
        os.environ["HAL_DATA"] = str(base / "data")
        os.environ["HAL_CONFIG"] = str(self.cfg)
        from halcal import caldav, connect, tools
        self.caldav, self.connect, self.tools = caldav, connect, tools
        self._client, self._sync = caldav.Client, tools.sync
        caldav.Client = FakeClient
        FakeClient.made = []
        self.synced = []
        tools.sync = lambda: self.synced.append(1) or {"calendars": ["Home"], "pulled": 4, "pushed": 1, "deleted": 0}
        self.lines = []

    def tearDown(self):
        self.caldav.Client, self.tools.sync = self._client, self._sync
        self.tmp.cleanup()

    def run_connect(self, argv, answers, passwords):
        answers, passwords = list(answers), list(passwords)
        prompts = []

        def ask(prompt):
            prompts.append(prompt)
            return answers.pop(0)

        def secret(prompt):
            prompts.append(prompt)
            return passwords.pop(0)

        code = self.connect.main(argv, ask=ask, secret=secret, out=self.lines.append)
        return code, prompts

    def caldav_settings(self):
        return tomllib.loads(self.cfg.read_text())["calendar"]["caldav"]

    def test_asks_for_everything_and_defaults_to_the_first_writable_calendar(self):
        code, prompts = self.run_connect([], ["me@icloud.com", ""], ["good-pass"])
        self.assertEqual(code, 0)
        self.assertIn("Apple ID", prompts[0])
        self.assertIn("[2]", prompts[-1])
        got = self.caldav_settings()
        self.assertEqual((got["username"], got["push_to"], got["url"]), ("me@icloud.com", "Home", self.connect.ICLOUD))
        pw = Path(got["password_file"])
        self.assertEqual(pw.read_text(), "good-pass")
        self.assertEqual(pw.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.synced, [1])
        self.assertTrue(any("4 pulled" in line for line in self.lines))
        self.assertTrue(any("(read-only)" in line for line in self.lines))
        self.assertFalse(any("good-pass" in line for line in self.lines))

    def test_choice_by_number_and_preset_push_to(self):
        self.run_connect(["--username", "me@icloud.com"], ["3"], ["good-pass"])
        self.assertEqual(self.caldav_settings()["push_to"], "Work")
        _, prompts = self.run_connect(["--username", "me@icloud.com", "--push-to", "Work"], [""], ["good-pass"])
        self.assertIn("[3]", prompts[-1])
        self.assertEqual(self.caldav_settings()["push_to"], "Work")

    def test_wrong_password_saves_nothing_and_says_why(self):
        code, _ = self.run_connect(["--username", "me@icloud.com"], [], ["bad", "bad", "bad"])
        self.assertEqual(code, 1)
        self.assertFalse(self.cfg.exists())
        self.assertFalse((self.cfg.parent / "caldav-password").exists())
        self.assertTrue(any("refused the username or app-specific password" in line for line in self.lines))
        self.assertTrue(any("Nothing was saved" in line for line in self.lines))
        self.assertEqual(self.synced, [])

    def test_wrong_then_right_password(self):
        code, _ = self.run_connect(["--username", "me@icloud.com"], [""], ["bad", "good-pass"])
        self.assertEqual(code, 0)
        self.assertEqual(self.caldav_settings()["push_to"], "Home")

    def test_rerunning_setup_updates_the_existing_block(self):
        self.cfg.write_text('[hal]\nvault = "~/v"\n\n[calendar.caldav]\nurl = "https://old.example"\n'
                            'username = "old@icloud.com"\ncalendars = ["Home"]\n\n[clock]\nsound = true\n')
        self.tools.setup_caldav("new@icloud.com", "good-pass", push_to="Work")
        text = self.cfg.read_text()
        self.assertEqual(text.count("[calendar.caldav]"), 1)
        data = tomllib.loads(text)
        got = data["calendar"]["caldav"]
        self.assertEqual((got["url"], got["username"], got["push_to"], got["calendars"]),
                         (self.connect.ICLOUD, "new@icloud.com", "Work", ["Home"]))
        self.assertEqual(data["clock"], {"sound": True})
        self.assertEqual(data["hal"]["vault"], "~/v")

    def test_setup_is_not_a_tool(self):
        spec = tomllib.loads((Path(__file__).resolve().parents[1] / "hal-module.toml").read_text())
        self.assertNotIn("setup_caldav", [t["function"] for t in spec["tools"]])
        params = {p for t in spec["tools"] for p in t.get("params", {})}
        self.assertNotIn("password", params)

    def test_cli_dispatches_connect(self):
        from halcal import __main__ as cli
        called, real = [], self.connect.main
        self.connect.main = lambda argv: called.append(argv) or 0
        try:
            self.assertEqual(cli.main(["connect", "--username", "x"]), 0)
        finally:
            self.connect.main = real
        self.assertEqual(called, [["--username", "x"]])


class PrivilegeTest(unittest.TestCase):
    def test_read_only_calendars_are_marked(self):
        import xml.etree.ElementTree as ET
        from halcal import caldav
        replies = {
            "<d:current-user-principal/>": '<d:multistatus xmlns:d="DAV:"><d:response><d:propstat><d:prop>'
            '<d:current-user-principal><d:href>/p/</d:href></d:current-user-principal></d:prop></d:propstat>'
            '</d:response></d:multistatus>',
            "<c:calendar-home-set/>": '<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            '<d:response><d:propstat><d:prop><c:calendar-home-set><d:href>/home/</d:href></c:calendar-home-set>'
            '</d:prop></d:propstat></d:response></d:multistatus>',
        }

        def cal(name, privs):
            listed = "".join(f"<d:privilege><d:{p}/></d:privilege>" for p in privs)
            return (f"<d:response><d:href>/home/{name}/</d:href><d:propstat><d:prop><d:displayname>{name}"
                    "</d:displayname><d:resourcetype><d:collection/><c:calendar/></d:resourcetype>"
                    + (f"<d:current-user-privilege-set>{listed}</d:current-user-privilege-set>" if privs else "")
                    + "</d:prop></d:propstat></d:response>")

        home = ('<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
                + cal("Home", ["read", "write"]) + cal("Shared", ["read"]) + cal("Plain", []) + "</d:multistatus>")
        c = caldav.Client("https://x.example/", "u", "p")
        c._propfind = lambda url, props, depth="0": ET.fromstring(replies.get(props, home))
        self.assertEqual([(x["name"], x["writable"]) for x in c.calendars()],
                         [("Home", True), ("Shared", False), ("Plain", True)])


if __name__ == "__main__":
    unittest.main()
