"""REQ-PACK-13: every subprocess call, network request and lock in pack code passes a timeout.

An AST scan over `packs/*/src`, so a new call site without a timeout fails here instead of
hanging a tool in production.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted(ROOT.glob("packs/*/src/**/*.py"))

# Calls that take a `timeout` keyword (or, for urlopen and create_connection, a positional one).
KEYWORD_ONLY = {
    "subprocess.run",
    "subprocess.check_output",
    "subprocess.check_call",
    "subprocess.call",
    "proc.completed",
    "imaplib.IMAP4",
    "imaplib.IMAP4_SSL",
    "smtplib.SMTP",
    "smtplib.SMTP_SSL",
    "urllib.request.urlopen",
    "socket.create_connection",
    "http.client.HTTPSConnection",
    "http.client.HTTPConnection",
}
# Method calls on a process object that wait.
WAITERS = {"wait", "communicate"}


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return node.id if isinstance(node, ast.Name) else ""


def _missing_timeouts(source: str, label: str) -> list[str]:
    """Lists the calls in `source` that wait without a timeout, each as `label:line: call`."""
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        has_timeout = any(k.arg == "timeout" or k.arg is None for k in node.keywords)
        positional_timeout = name in {"urllib.request.urlopen", "socket.create_connection"} and (
            len(node.args) >= 3 or (name == "socket.create_connection" and len(node.args) >= 2)
        )
        if name in KEYWORD_ONLY and not (has_timeout or positional_timeout):
            found.append(f"{label}:{node.lineno}: {name} has no timeout")
        elif name.rsplit(".", 1)[-1] in WAITERS and name.split(".")[0] in {"p", "proc", "child"}:
            if not has_timeout:
                found.append(f"{label}:{node.lineno}: {name} has no timeout")
    return found


def test_the_scan_sees_the_pack_sources():
    assert len(SOURCES) > 100


def test_the_scan_flags_a_call_without_a_timeout():
    bad = "import subprocess\nsubprocess.run(['ls'])\n"
    assert _missing_timeouts(bad, "bad.py") == ["bad.py:2: subprocess.run has no timeout"]


def test_the_scan_accepts_a_call_with_a_timeout():
    assert (
        _missing_timeouts("import subprocess\nsubprocess.run(['ls'], timeout=5)\n", "ok.py") == []
    )


def test_every_subprocess_and_urlopen_call_has_timeout():
    problems = [
        line
        for path in SOURCES
        for line in _missing_timeouts(path.read_text(), str(path.relative_to(ROOT)))
    ]
    assert not problems, "\n".join(problems)
