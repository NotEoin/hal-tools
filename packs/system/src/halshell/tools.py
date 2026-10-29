"""hal-shell's tools: the fallback that lets Hal do anything the command line can.

shell_look runs only commands that read: every command in a pipeline must be
on the read-only list, and redirection to files, command substitution and
background jobs are refused. shell_run runs anything, and is marked confirm in
the manifest, so hal-hub asks the user first. Output is cut to a readable size.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess

from .config import settings

READ_ONLY = {
    "ls",
    "cat",
    "head",
    "tail",
    "less",
    "wc",
    "grep",
    "rg",
    "find",
    "locate",
    "file",
    "stat",
    "du",
    "df",
    "free",
    "uptime",
    "whoami",
    "id",
    "date",
    "cal",
    "uname",
    "hostname",
    "ps",
    "pgrep",
    "top",
    "lsblk",
    "lscpu",
    "lsusb",
    "lspci",
    "ip",
    "ss",
    "ping",
    "dig",
    "host",
    "nslookup",
    "which",
    "whereis",
    "type",
    "echo",
    "printf",
    "printenv",
    "sort",
    "uniq",
    "cut",
    "tr",
    "awk",
    "sed",
    "jq",
    "column",
    "diff",
    "cmp",
    "md5sum",
    "sha256sum",
    "tree",
    "realpath",
    "basename",
    "dirname",
    "journalctl",
    "dmesg",
    "sensors",
    "nvidia-smi",
    "git",
    "apt",
    "dpkg",
    "snap",
    "flatpak",
    "systemctl",
    "loginctl",
    "timedatectl",
    "hostnamectl",
    "lsof",
    "last",
    "w",
    "who",
    "groups",
    "getent",
    "xdg-mime",
    "gsettings",
    "nmcli",
    "pactl",
    "wpctl",
    "docker",
    "ollama",
    "seq",
    "true",
    "test",
    "bc",
    "numfmt",
    "zcat",
    "tar",
    "unzip",
    "pdftotext",
    "identify",
    "ffprobe",
    "exiftool",
}
# Subcommands that change things, refused by shell_look even though the command itself is listed.
WRITES = {
    "git": {
        "push",
        "commit",
        "reset",
        "checkout",
        "rebase",
        "merge",
        "clean",
        "rm",
        "mv",
        "restore",
        "switch",
        "branch",
        "tag",
        "stash",
        "pull",
        "fetch",
        "am",
        "apply",
        "cherry-pick",
        "revert",
        "init",
        "clone",
        "config",
    },
    "systemctl": {
        "start",
        "stop",
        "restart",
        "enable",
        "disable",
        "mask",
        "unmask",
        "kill",
        "reload",
        "edit",
        "daemon-reload",
        "set-property",
        "poweroff",
        "reboot",
        "suspend",
        "hibernate",
        "isolate",
    },
    "apt": {
        "install",
        "remove",
        "purge",
        "upgrade",
        "full-upgrade",
        "autoremove",
        "update",
        "dist-upgrade",
    },
    "snap": {"install", "remove", "refresh", "disable", "enable"},
    "flatpak": {"install", "uninstall", "update"},
    "docker": {
        "run",
        "rm",
        "rmi",
        "stop",
        "kill",
        "exec",
        "build",
        "pull",
        "push",
        "prune",
        "system",
        "compose",
    },
    "ollama": {"rm", "pull", "push", "create", "cp", "run", "stop"},
    "gsettings": {"set", "reset"},
    "nmcli": {"connection", "device", "radio", "networking", "general"},
    "ip": {"link", "addr", "route"},
    "tar": {"-x", "x", "--extract", "-c", "c", "--create"},
    "sed": {"-i", "--in-place"},
    "dpkg": {"-i", "--install", "-r", "--remove", "-P", "--purge", "--configure"},
    "journalctl": {"--vacuum-size", "--vacuum-time", "--vacuum-files", "--rotate", "--flush"},
    "find": {"-delete", "-exec", "-execdir", "-ok", "-fprint"},
    "unzip": {"-o"},
    "loginctl": {"terminate-session", "kill-session", "lock-session", "poweroff", "reboot"},
    "timedatectl": {"set-time", "set-timezone", "set-ntp"},
    "hostnamectl": {"set-hostname"},
}
# awk and sed can run programs or write files from inside their scripts.
SCRIPT_ESCAPES = re.compile(r"system\s*\(|getline|\|\s*\"|print\s*\||\bw\s+\S|\be\s|/e\b")
UNSAFE = re.compile(r"[`]|\$\(|(?<![<>])>(?!&)|>>|&\s*$|;|\|\||&&")


def _check_read_only(command: str) -> None:
    if UNSAFE.search(command):
        raise PermissionError(
            "redirection, chaining and substitution are not read-only; use shell_run"
        )
    for part in command.split("|"):
        words = shlex.split(part)
        if not words:
            continue
        prog = os.path.basename(words[0])
        if prog not in READ_ONLY:
            raise PermissionError(f"{prog} is not on the read-only list; use shell_run")
        bad = WRITES.get(prog, set()).intersection(w.split("=", 1)[0] for w in words[1:])
        if bad:
            raise PermissionError(f"{prog} {sorted(bad)[0]} changes things; use shell_run")
        if prog in ("awk", "sed") and any(SCRIPT_ESCAPES.search(w) for w in words[1:]):
            raise PermissionError(f"{prog} scripts that run commands or write files need shell_run")
        if prog == "git" and any(w == "-c" or w.startswith("--exec-path") for w in words[1:]):
            raise PermissionError("git -c can run commands; use shell_run")


def _exec(command: str, cwd: str, timeout: float) -> dict:
    done = subprocess.run(
        ["bash", "-c", command],
        cwd=os.path.expanduser(cwd or "~"),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    limit = int(settings()["max_output"])
    out = done.stdout
    return {
        "exit_code": done.returncode,
        "output": out[:limit] + ("\n[cut]" if len(out) > limit else ""),
        "errors": done.stderr[-2000:],
    }


def look(command: str, cwd: str = "") -> dict:
    """Runs a read-only command (or pipeline of them) and returns its output."""
    _check_read_only(command)
    return _exec(command, cwd, 60)


def run(command: str, cwd: str = "", timeout: int = 300) -> dict:
    """Runs any shell command. Confirmation is required through hal-hub."""
    return _exec(command, cwd, int(timeout))
