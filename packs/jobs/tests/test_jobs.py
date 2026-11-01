"""Tests for hal-jobs' tools, with jobhunt's command line faked: no job data is read or changed."""

import inspect
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from haljobs import tools

MANIFEST = Path(__file__).resolve().parents[1] / "src" / "haljobs" / "hal-module.toml"


class FakeJobhunt:
    """Stands in for proc.completed, recording each jobhunt command and printing `stdout`."""

    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr, self.calls = stdout, returncode, stderr, []

    def __call__(self, argv, cwd=None, timeout=None, **kwargs):
        self.calls.append((argv[3:], timeout))
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "jobhunt").mkdir()
        config = self.root / "config.toml"
        config.write_text(f'[jobs]\njobhunt_root = "{self.root}"\n')
        patcher = mock.patch.dict(os.environ, {"HAL_CONFIG": str(config)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_with(self, fake, fn, *args, **kwargs):
        with mock.patch.object(tools.proc, "completed", fake):
            return fn(*args, **kwargs)


class LayoutTest(Sandbox):
    def test_queue_and_applications_read_the_command_line_not_a_web_api(self):
        # the current jobhunt has no unauthenticated web API, so these must not touch the network
        fake = FakeJobhunt("one\ntwo")
        with mock.patch("socket.socket", side_effect=AssertionError("network used")):
            queued = self.run_with(fake, tools.queue)
            applied = self.run_with(fake, tools.applications)
        self.assertEqual(queued, {"jobs": ["one", "two"]})
        self.assertEqual(applied, [{"line": "one"}, {"line": "two"}])
        self.assertEqual([c[0][:1] for c in fake.calls], [["queue"], ["list"]])


class ArgumentTest(Sandbox):
    def test_option_like_job_id_stays_after_the_separator(self):
        # a job id such as "--help" must reach jobhunt as data, not as an option
        fake = FakeJobhunt("ok")
        self.run_with(fake, tools.mark, "--help", "applied")
        argv = fake.calls[0][0]
        self.assertLess(argv.index("--"), argv.index("--help"))

    def test_checkout_venv_python_is_used_when_present(self):
        seen = []

        def fake(argv, cwd=None, timeout=None, **kwargs):
            seen.append(argv[0])
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.run_with(fake, tools.todo)
        self.assertEqual(seen[-1], tools.SYSTEM_PYTHON)
        python = self.root / ".venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\n")
        python.chmod(0o755)
        self.run_with(fake, tools.todo)
        self.assertEqual(seen[-1], str(python))


class MarkTest(Sandbox):
    def test_unknown_status_is_refused(self):
        with self.assertRaises(ValueError):
            tools.mark("any", "hired-yesterday")

    def test_shortlisted_is_accepted(self):
        fake = FakeJobhunt("Arm | Graduate Engineer -> shortlisted")
        self.assertEqual(
            self.run_with(fake, tools.mark, "arm-1", "shortlisted"),
            "Arm | Graduate Engineer -> shortlisted",
        )
        self.assertEqual(fake.calls[0][0], ["set", "--", "arm-1", "shortlisted"])

    def test_shortlist_with_note(self):
        fake = FakeJobhunt("ok")
        self.run_with(fake, tools.shortlist, "arm-1", note="good fit")
        self.assertEqual(fake.calls[0][0], ["set", "--", "arm-1", "shortlisted", "good fit"])

    def test_jobhunt_failure_is_raised(self):
        fake = FakeJobhunt(returncode=1, stderr="2 jobs match 'arm'")
        with self.assertRaisesRegex(RuntimeError, "2 jobs match"):
            self.run_with(fake, tools.shortlist, "arm")

    def test_missing_checkout_is_explained(self):
        (self.root / "jobhunt").rmdir()
        with self.assertRaisesRegex(RuntimeError, "jobhunt_root"):
            self.run_with(FakeJobhunt(), tools.shortlist, "arm")


class ReadToolsTest(Sandbox):
    def test_status_digest_is_printed_not_emailed(self):
        fake = FakeJobhunt("Job search: 2 need you\n\n...")
        self.assertTrue(self.run_with(fake, tools.status_digest).startswith("Job search"))
        self.assertEqual(fake.calls[0][0], ["digest", "--dry-run"])

    def test_matches(self):
        fake = FakeJobhunt(
            "  71  new  Arm  Graduate Engineer  London\n      arm-1  | fits\n(1 shown)"
        )
        self.assertIn("arm-1", self.run_with(fake, tools.matches))
        self.assertEqual(fake.calls[0][0], ["list", "-m", "60", "-n", "8"])
        self.run_with(fake, tools.matches, min_score=72.5, limit=3)
        self.assertEqual(fake.calls[1][0], ["list", "-m", "72.5", "-n", "3"])


class TodoAddTest(Sandbox):
    def test_adds_and_returns_the_list(self):
        fake = FakeJobhunt("  12  ring Arm back")
        self.assertEqual(
            self.run_with(fake, tools.todo_add, "  ring Arm back "), "12  ring Arm back"
        )
        self.assertEqual(fake.calls[0][0], ["todo", "add", "--", "ring Arm back"])

    def test_empty_text_is_refused(self):
        fake = FakeJobhunt()
        with self.assertRaises(ValueError):
            self.run_with(fake, tools.todo_add, "   ")
        self.assertEqual(fake.calls, [])


class PackTest(Sandbox):
    def test_returns_the_pack_and_its_pdfs(self):
        out = self.root / "packs" / "arm-graduate-engineer"
        out.mkdir(parents=True)
        for name in ("pack.md", "cv.pdf", "cover-letter.pdf"):
            (out / name).write_text("x")
        fake = FakeJobhunt(f"arm-1: drafting...\n  {out / 'pack.md'}\n")
        result = self.run_with(fake, tools.pack, "arm-1")
        self.assertEqual(fake.calls[0], (["pack", "--", "arm-1"], tools.PACK_TIMEOUT))
        self.assertEqual(result["pack"], str(out / "pack.md"))
        self.assertEqual(
            result["files"], [str(out / n) for n in ("pack.md", "cover-letter.pdf", "cv.pdf")]
        )
        self.assertIn("drafting", result["output"])

    def test_no_pack_path_gives_no_files(self):
        result = self.run_with(FakeJobhunt("nothing drafted"), tools.pack, "arm-1")
        self.assertEqual((result["pack"], result["files"]), (None, []))


class ManifestTest(unittest.TestCase):
    def test_every_tool_matches_a_function(self):
        spec = tomllib.loads(MANIFEST.read_text())
        for t in spec["tools"]:
            fn = getattr(tools, t.get("function", t["name"]))
            accepted = set(inspect.signature(fn).parameters)
            self.assertLessEqual(set(t.get("params", {})), accepted, t["name"])
            for name, p in t.get("params", {}).items():
                if p.get("required"):
                    self.assertIs(
                        inspect.signature(fn).parameters[name].default, inspect.Parameter.empty
                    )

    def test_new_tools_are_declared(self):
        spec = {t["name"]: t for t in tomllib.loads(MANIFEST.read_text())["tools"]}
        for name in ("jobs_status", "jobs_matches", "jobs_shortlist", "jobs_todo_add", "jobs_pack"):
            self.assertIn(name, spec)
        self.assertEqual(spec["jobs_pack"]["timeout"], tools.PACK_TIMEOUT)
        self.assertIn("shortlisted", spec["jobs_mark"]["params"]["status"]["enum"])

    def test_every_tool_that_echoes_job_text_marks_its_output_untrusted(self):
        # jobs_mark, jobs_shortlist, jobs_todo_add and jobs_stats print company, title or to-do
        # text from job pages and emails, yet reached the agent as trusted output (prompt injection)
        trusted = {"jobs_open"}  # returns only the configured Hal Employment URL
        for t in tomllib.loads(MANIFEST.read_text())["tools"]:
            if t["name"] not in trusted:
                self.assertIs(t.get("untrusted_output"), True, t["name"])


if __name__ == "__main__":
    unittest.main()
