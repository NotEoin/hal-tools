"""Tests for the read-only gate."""
import sys
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halshell import tools  # noqa: E402


class ShellTest(unittest.TestCase):
    @pytest.mark.host  # runs real programs
    def test_reads_are_allowed(self):
        self.assertEqual(tools.look("echo hi | tr a-z A-Z")["output"].strip(), "HI")
        tools.look("git -C . log -1 --oneline")
        tools.look("ls -la ~ 2>&1 | head -3")
        tools.look("df -h | awk '{print $5}'")
        tools.look("printf 'a b' | sed 's/a/c/'")

    def test_writes_are_refused(self):
        for cmd in ("rm -rf /tmp/x", "echo hi > /tmp/x", "ls; rm x", "ls && rm x", "cat $(echo /etc/passwd)",
                    "git push", "systemctl stop foo", "find . -delete", "sed -i s/a/b/ f", "python3 -c 'print(1)'",
                    "apt install vim", "sleep 100 &", "ls `rm x`", "ls | xargs rm",
                    "awk 'BEGIN{system(\"rm x\")}'", "env rm x", "python3 evil.py", "git -c alias.x=!rm x",
                    "dpkg -i x.deb", "sed 's/a/b/e' f", "journalctl --vacuum-time=1s"):
            # Only the check runs: a test of the gate must never execute what it refuses.
            with self.assertRaises(PermissionError, msg=cmd):
                tools._check_read_only(cmd)


if __name__ == "__main__":
    unittest.main()
