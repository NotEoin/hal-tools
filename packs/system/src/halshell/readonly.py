"""The `shell_look` command table and its argv checker (REQ-PACK-20, REQ-PACK-21).

`check` splits a command string with `shlex`, refuses shell grammar, looks the program up in a
fixed table and validates every option and positional against that program's entry. It returns
an absolute argv list for the capped runner; no shell is ever started, so what is not on the
table cannot run. Design decisions: programs resolve only from system directories (never the
user's `PATH`); a program with a write verb or a code-running option is simply absent from the
table; every path goes through a caller-supplied `path_ok` because the single `command` string
escapes the broker's per-parameter path check.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

SYSTEM_DIRS = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")  # never the user's PATH
GRAMMAR_CHARS = frozenset("|;&<>()")  # lexer punctuation; a token of only these is grammar
GRAMMAR_PARTS = ("`", "$(", "<(", "\n", "\r", "\0")
MAX_INT = 100000  # an upper bound for any numeric option
MAX_JOURNAL_LINES = 1000  # journalctl -n
MAX_PATTERN = 200
MAX_TIME = 40
UNIT = re.compile(r"[A-Za-z0-9@._:\-]{1,128}")
NAME = re.compile(r"[A-Za-z0-9._+\-]{1,128}")
TIME = re.compile(rf"[0-9A-Za-z :.\-+]{{1,{MAX_TIME}}}")
FIELDS = re.compile(r"[A-Za-z0-9_.%,]{1,200}")
PS_FIELDS = frozenset("pid ppid user %cpu %mem etime stat comm rss vsz".split())
PS_DEFAULT = ("-eo", "pid,ppid,user,%cpu,%mem,etime,comm")


class NotAllowed(PermissionError):
    """The command is not on the read-only table, or an argument breaks the table's rules."""


@dataclass(frozen=True)
class CommandSpec:
    """One program's entry: what may follow it."""

    flags: frozenset[str] = frozenset()
    valued: Mapping[str, str] = field(default_factory=dict)
    positionals: tuple[str, ...] = ()  # kind of the first, then of every later one
    max_positionals: int = 0
    subcommands: frozenset[str] | None = None
    chain: Mapping[str, tuple[frozenset[str], bool]] | None = None  # sub -> (next words, required)
    require: tuple[tuple[str, ...], ...] = ()  # each tuple: at least one of these options
    append: tuple[str, ...] = ()
    default: tuple[str, ...] = ()  # used when no positional or option was given
    paths_first: bool = False  # find: paths must come before the expression


def _s(
    flags: str = "",
    valued: Mapping[str, str] | None = None,
    pos: tuple[str, ...] = (),
    n: int = 0,
    **kw,
) -> CommandSpec:
    return CommandSpec(frozenset(flags.split()), valued or {}, pos, n, **kw)


def _subs(words: str) -> frozenset[str]:
    return frozenset(words.split())


_ENUM_PRIO = "enum:emerg|alert|crit|err|warning|notice|info|debug"
TABLE: Mapping[str, CommandSpec] = {
    "ls": _s("-l -a -A -h -t -r -S -1 -d -R -F", pos=("path",), n=8, append=("--color=never",)),
    "stat": _s("-L -t", pos=("path",), n=8),
    "file": _s("-b -i -L -z", pos=("path",), n=8),
    "wc": _s("-l -w -c -m", pos=("path",), n=8),
    "head": _s(valued={"-n": "int", "-c": "int"}, pos=("path",), n=4),
    "tail": _s(valued={"-n": "int", "-c": "int"}, pos=("path",), n=4),
    "cat": _s("-n", pos=("path",), n=4),
    "du": _s("-s -h -a -c", {"-d": "int", "--max-depth": "int"}, ("path",), 4),
    "df": _s("-h -T -i -l", pos=("path",), n=4),
    "free": _s("-h -m -g -b -t"),
    "uptime": _s("-p -s"),
    "whoami": _s(),
    "id": _s("-u -g -n -G", pos=("name",), n=1),
    "groups": _s(pos=("name",), n=1),
    "lscpu": _s("-e -p"),
    "lsusb": _s("-t -v"),
    "sensors": _s("-f -u"),
    "w": _s("-h"),
    "who": _s("-a -b -H -q"),
    "uname": _s("-a -r -m -s -n -o"),
    "hostname": _s("-f -I -s"),
    "date": _s("-u -R -I --iso-8601", pos=("dateformat",), n=1),
    "lsblk": _s("-f -a -m -p", pos=("path",), n=4),
    "lspci": _s("-k -v -nn"),
    "ps": _s(
        "-e -A -H",
        {"-u": "name", "-p": "int", "-o": "fields:ps", "--sort": "fields:ps"},
        default=PS_DEFAULT,
    ),
    "pgrep": _s("-l -c -x", {"-u": "name"}, ("pattern",), 1),
    "ip": CommandSpec(
        flags=_subs("-br -4 -6 -j -s"),
        positionals=("name",),
        max_positionals=1,
        subcommands=_subs("addr address link route neigh"),
        chain={k: (_subs("show list"), False) for k in "addr address link route neigh".split()},
    ),
    "ss": _s("-t -u -l -n -p -a -4 -6 -s -x -H"),
    "systemctl": CommandSpec(
        flags=_subs("--user --failed --all -a"),
        valued={"--type": "name", "--state": "name", "-p": "name", "-n": "int"},
        positionals=("unit",),
        max_positionals=8,
        subcommands=_subs(
            "status is-active is-enabled is-failed list-units list-timers list-unit-files show cat"
        ),
        append=("--no-pager",),
    ),
    "journalctl": _s(
        "--user -k -b -r -q --utc",
        {
            "-u": "unit",
            "-p": _ENUM_PRIO,
            "-n": "jlines",
            "--since": "time",
            "--until": "time",
            "-o": "enum:short|short-iso|cat|json",
        },
        append=("--no-pager",),
    ),
    "dpkg": _s("-l", {"-s": "name", "-L": "name"}, ("pattern",), 1),
    "apt": CommandSpec(
        flags=_subs("--installed --upgradable"),
        positionals=("name",),
        max_positionals=4,
        subcommands=_subs("list show policy"),
    ),
    "snap": CommandSpec(positionals=("name",), max_positionals=1, subcommands=_subs("list info")),
    "flatpak": CommandSpec(
        positionals=("name",), max_positionals=1, subcommands=_subs("list info")
    ),
    "which": _s(pos=("name",), n=8),
    "whereis": _s(pos=("name",), n=8),
    "realpath": _s("-e -f", pos=("path",), n=8),
    "readlink": _s("-e -f", pos=("path",), n=8),
    "findmnt": _s("-l -n", {"-T": "path"}),
    "timedatectl": CommandSpec(subcommands=_subs("status show")),
    "hostnamectl": CommandSpec(subcommands=_subs("status show")),
    "localectl": CommandSpec(subcommands=_subs("status show")),
    "loginctl": CommandSpec(
        positionals=("name",),
        max_positionals=1,
        subcommands=_subs("list-sessions show-session session-status"),
    ),
    "nmcli": CommandSpec(
        flags=_subs("-t"),
        valued={"-f": "fields"},
        positionals=("name",),
        max_positionals=1,
        subcommands=_subs("general device connection radio"),
        chain={
            "general": (_subs("status"), True),
            "device": (_subs("status"), True),
            "connection": (_subs("show"), True),
            "radio": (_subs("all wifi"), False),
        },
    ),
    "find": _s(
        "-empty -print",
        {
            "-name": "pattern",
            "-iname": "pattern",
            "-path": "pattern",
            "-type": "enum:f|d|l",
            "-maxdepth": "int",
            "-mindepth": "int",
            "-size": "pattern",
            "-mtime": "pattern",
            "-mmin": "pattern",
        },
        ("path",),
        4,
        paths_first=True,
    ),
    "grep": _s(
        "-r -i -n -l -c -w -F -E -s -h -H",
        {
            "-m": "int",
            "-C": "int",
            "-A": "int",
            "-B": "int",
            "--include": "pattern",
            "--exclude": "pattern",
        },
        ("pattern", "path"),
        9,
    ),
    "rg": _s(
        "-i -n -l -c -w -F -S --hidden --no-ignore",
        {"-m": "int", "-C": "int", "-g": "pattern", "--glob": "pattern"},
        ("pattern", "path"),
        9,
    ),
    "tree": _s("-a -d -f", {"-L": "int"}, ("path",), 1),
    "tar": _s("-t -v -z -j -J", {"-f": "path"}, require=(("-t",), ("-f",))),
    "unzip": _s("-l -v", pos=("path",), n=1, require=(("-l", "-v"),)),
    "pdftotext": _s("-layout", {"-f": "int", "-l": "int"}, ("path",), 1, append=("-",)),
    "ffprobe": _s(
        "-hide_banner -show_format -show_streams",
        {"-v": "enum:error|quiet|warning", "-of": "enum:json|default"},
        ("path",),
        1,
    ),
    "nvidia-smi": _s("-L", {"--query-gpu": "fields", "--format": "enum:csv"}),
}
# Options that take their value attached to the option letter (`head -n5`).
ATTACHED_OK = frozenset({"-n", "-c", "-d", "-m", "-C", "-A", "-B", "-L", "-f", "-l", "-p", "-s"})
PathOk = Callable[[Path], "str | None"]


def resolve_program(name: str) -> str:
    """The absolute path of `name` in the system directories; raises `NotAllowed` if absent."""
    for d in SYSTEM_DIRS:
        p = Path(d) / name
        if p.is_file():
            return str(p)
    raise NotAllowed(f"{name} is not installed in {', '.join(SYSTEM_DIRS)}")


def _tokens(command: str) -> list[str]:
    if any(part in command for part in GRAMMAR_PARTS):
        raise NotAllowed(_GRAMMAR_MSG)
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        words = list(lex)
    except ValueError as exc:
        raise NotAllowed(f"cannot parse the command: {exc}") from exc
    if any(set(w) <= GRAMMAR_CHARS for w in words):
        raise NotAllowed(_GRAMMAR_MSG)
    if not words:
        raise NotAllowed("empty command")
    return words


_GRAMMAR_MSG = (
    "shell grammar (pipes, redirects, chaining, substitution) is not available; run one "
    "program and use the filter and head arguments to cut its output"
)


def _value(kind: str, value: str, what: str, path_ok: PathOk, cwd: Path) -> str:
    ok = True
    if kind == "int":
        ok = value.isdigit() and int(value) <= MAX_INT
    elif kind == "jlines":
        ok = value.isdigit() and int(value) <= MAX_JOURNAL_LINES
    elif kind == "unit":
        ok = UNIT.fullmatch(value) is not None
    elif kind == "name":
        ok = NAME.fullmatch(value) is not None
    elif kind == "time":
        ok = TIME.fullmatch(value) is not None
    elif kind == "pattern":
        ok = 0 < len(value) <= MAX_PATTERN and not value.startswith("-")
    elif kind == "fields":
        ok = FIELDS.fullmatch(value) is not None
    elif kind == "fields:ps":
        ok = all(f in PS_FIELDS or f.lstrip("-+") in PS_FIELDS for f in value.split(","))
    elif kind == "dateformat":
        ok = value.startswith("+") and len(value) <= MAX_PATTERN
    elif kind.startswith("enum:"):
        ok = value in kind[5:].split("|")
    elif kind == "path":
        return _path(value, what, path_ok, cwd)
    if not ok:
        raise NotAllowed(f"{what}: {value!r} is not a valid {kind.split(':')[0]}")
    return value


def _path(value: str, what: str, path_ok: PathOk, cwd: Path) -> str:
    if not value or value.startswith("-") or "://" in value:
        raise NotAllowed(f"{what}: {value!r} is not a plain path")
    resolved = (cwd / Path(value).expanduser()).resolve(strict=False)
    reason = path_ok(resolved)
    if reason:
        raise NotAllowed(f"{what}: {reason}")
    return str(resolved)  # the checked path itself, so a symlink cannot change after the check


def _split_option(tok: str, spec: CommandSpec) -> list[tuple[str, str | None]]:
    """Maps one option token to `(name, attached value or None)` pairs; raises if unknown."""
    if tok.startswith("--"):
        name, eq, val = tok.partition("=")
        if name in spec.valued and eq:
            return [(name, val)]
        if name in spec.valued or (name in spec.flags and not eq):
            return [(name, None)]
        raise NotAllowed(f"option {name} is not allowed")
    if tok in spec.flags or tok in spec.valued:
        return [(tok, None)]
    letters, out = tok[1:], []
    for i, ch in enumerate(letters):
        name = "-" + ch
        if name in spec.flags:
            out.append((name, None))
        elif name in spec.valued and name in ATTACHED_OK:
            out.append((name, letters[i + 1 :] or None))
            break
        else:
            raise NotAllowed(f"option {tok} is not allowed (at {name})")
    return out


def _options(prog, spec, words, path_ok, cwd):
    """Returns (option argv, option names seen, positional words)."""
    out, seen, pos, expr = [], set(), [], False
    it = iter(words)
    for tok in it:
        if not tok.startswith("-") or tok == "-":
            if expr:
                raise NotAllowed(f"{prog}: paths must come before the expression")
            pos.append(tok)
            continue
        if tok == "--":
            raise NotAllowed("`--` is not allowed")
        for name, val in _split_option(tok, spec):
            seen.add(name)
            if name not in spec.valued:
                out.append(name)
                continue
            if val is None:
                val = next(it, None)
                if val is None:
                    raise NotAllowed(f"{prog} {name} needs a value")
            val = _value(spec.valued[name], val, f"{prog} {name}", path_ok, cwd)
            out += [f"{name}={val}"] if name.startswith("--") else [name, val]
        expr = spec.paths_first
    return out, seen, pos


def _subcommand(prog, spec, pos):
    """Splits the leading subcommand words off `pos`; returns (words, rest)."""
    if spec.subcommands is None:
        return [], pos
    if not pos or pos[0] not in spec.subcommands:
        raise NotAllowed(f"{prog} needs one of: {', '.join(sorted(spec.subcommands))}")
    words, rest = [pos[0]], pos[1:]
    if spec.chain and words[0] in spec.chain:
        nxt, required = spec.chain[words[0]]
        if rest and rest[0] in nxt:
            words.append(rest[0])
            rest = rest[1:]
        elif required:
            raise NotAllowed(f"{prog} {words[0]} needs one of: {', '.join(sorted(nxt))}")
        if prog == "nmcli" and rest and words != ["connection", "show"]:
            raise NotAllowed("nmcli takes a connection name only after `connection show`")
    return words, rest


def check(command: str, *, path_ok: PathOk, cwd: Path) -> list[str]:
    """Validates `command` against the table; returns the absolute argv to run.

    Relative paths resolve against `cwd`. Raises `NotAllowed` for shell grammar, an unknown
    program, option or subcommand, a bad positional, or a path that `path_ok` refuses (it
    returns a reason, or `None` when the path is fine).
    """
    words = _tokens(command)
    prog = words[0]
    spec = TABLE.get(prog)
    if spec is None:
        raise NotAllowed(f"{prog} is not on the read-only command list")
    opts, seen, pos = _options(prog, spec, words[1:], path_ok, cwd)
    sub, pos = _subcommand(prog, spec, pos)
    kinds = spec.positionals
    if len(pos) > spec.max_positionals or (pos and not kinds):
        raise NotAllowed(f"{prog}: too many arguments (at most {spec.max_positionals})")
    args = [
        _value(kinds[min(i, len(kinds) - 1)], p, f"{prog} argument", path_ok, cwd)
        for i, p in enumerate(pos)
    ]
    for group in spec.require:
        if not seen.intersection(group):
            raise NotAllowed(f"{prog} needs {' or '.join(group)}")
    if spec.default and "-o" not in seen:
        opts += list(spec.default)
    ordered = args + opts if spec.paths_first else opts + sub + args
    return [resolve_program(prog), *ordered, *spec.append]
