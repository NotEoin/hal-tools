"""hal-routines' tools: scenes, schedules and triggers built from other modules' tools.

A scene is a named list of tool calls such as "focus": do-not-disturb for an hour, warm lights,
music paused. Each step is its own `halhub.client.call`, so policy decides every step and nothing
here confirms a call. Schedules run a scene or
a single tool at a time, once or repeating; triggers run one when something
happens. The daemon (python -m halroutines.daemon) runs schedules and triggers.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime

from halhub import client as hub_client
from halhub.client import RoutineRun, ToolDenied, ToolFailed
from halkit import when

from .settings import data_dir, settings

log = logging.getLogger(__name__)

CALLER = "routines"  # the module name the hub checks against `calls` inside a worker
STEP_TIMEOUT_S = 600.0  # the longest `routines_run` may take (its manifest timeout)
URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.I)


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "routines.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS scenes (name TEXT PRIMARY KEY, steps TEXT);
        CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY, target TEXT, args TEXT, at
        REAL,
            rrule TEXT, label TEXT);
        CREATE TABLE IF NOT EXISTS triggers (id INTEGER PRIMARY KEY, event TEXT, target TEXT,
        args TEXT,
            last REAL DEFAULT 0);
    """)
    migrate(con)
    return con


def upgrade_step(tool: str, args: dict) -> tuple[str, dict]:
    """A stored step in today's schema: `desktop_open` takes `url` or `path`, not `target`, and
    `desktop_clipboard` with `text` became `desktop_clipboard_set`."""
    if tool == "desktop_open" and "target" in args:
        rest = {k: v for k, v in args.items() if k != "target"}
        key = "url" if URL_RE.match(str(args["target"])) else "path"
        return tool, {**rest, key: args["target"]}
    if tool == "desktop_clipboard" and "text" in args:
        return "desktop_clipboard_set", args
    return tool, args


def migrate(con: sqlite3.Connection) -> int:
    """Rewrites stored steps that use a retired tool schema; returns the rows changed."""
    changed = 0
    for row in con.execute("SELECT name, steps FROM scenes").fetchall():
        steps = json.loads(row["steps"])
        new = []
        for st in steps:
            tool, args = upgrade_step(st.get("tool", ""), st.get("args") or {})
            new.append(
                {**st, "tool": tool, "args": args}
                if tool != st.get("tool") or args != (st.get("args") or {})
                else st
            )
        if new != steps:
            con.execute(
                "UPDATE scenes SET steps = ? WHERE name = ?", (json.dumps(new), row["name"])
            )
            changed += 1
    for table in ("schedules", "triggers"):
        for row in con.execute(f"SELECT id, target, args FROM {table}").fetchall():  # noqa: S608 - fixed table names
            tool, args = upgrade_step(row["target"], json.loads(row["args"] or "{}"))
            if (tool, args) != (row["target"], json.loads(row["args"] or "{}")):
                con.execute(
                    f"UPDATE {table} SET target = ?, args = ? WHERE id = ?",  # noqa: S608 - fixed table names
                    (tool, json.dumps(args), row["id"]),
                )
                changed += 1
    if changed:
        con.commit()
        log.info("upgraded %d stored routine row(s) to the current tool schemas", changed)
    return changed


def call_tool(tool: str, args: dict | None = None, *, routine: RoutineRun | None = None) -> dict:
    """Runs one tool through `halhub.client.call`; policy decides it, nothing here confirms it.

    Returns `{"result": ...}` or, for a refused or failed call, `{"error": ..., "denied": bool}`.
    """
    try:
        result = hub_client.call(
            tool,
            args or {},
            CALLER,
            unattended=routine is not None,
            routine=routine,
            timeout=STEP_TIMEOUT_S,
        )
    except ToolDenied as exc:
        return {"error": str(exc), "denied": True}
    except ToolFailed as exc:
        return {"error": str(exc), "denied": False}
    return {"result": result}


def scenes() -> dict:
    """Every scene, the built-in ones from config and those saved by asking Hal."""
    out = dict(settings()["scenes"])
    for r in _db().execute("SELECT * FROM scenes"):
        out[r["name"]] = json.loads(r["steps"])
    return out


def run_scene(name: str) -> dict:
    """Runs every step of a scene through the hub; a refused or failing step does not stop the rest.

    Returns `{"scene": name, "steps": [{"tool", "status": "ok" | "error" | "skipped", "reason"}]}`.
    """
    all_scenes = scenes()
    key = next((k for k in all_scenes if k.lower() == name.lower()), None)
    if key is None:
        raise ValueError(f"no scene {name!r}; have {', '.join(all_scenes)}")
    return {"scene": key, "steps": run_steps(all_scenes[key])}


def run_steps(steps: list[dict], *, routine: RoutineRun | None = None) -> list[dict]:
    """Calls each step as its own hub call and returns one outcome per step."""
    outcomes = []
    for step in steps:
        out = call_tool(step["tool"], step.get("args"), routine=routine)
        if "error" not in out:
            outcomes.append({"tool": step["tool"], "status": "ok", "reason": ""})
        else:
            status = "skipped" if out["denied"] else "error"
            outcomes.append({"tool": step["tool"], "status": status, "reason": out["error"]})
    return outcomes


def save_scene(name: str, steps: list | str) -> dict:
    """Saves a scene: a list of {"tool": ..., "args": {...}} steps."""
    parsed = json.loads(steps) if isinstance(steps, str) else steps
    if not isinstance(parsed, list) or not all(isinstance(s, dict) and "tool" in s for s in parsed):
        raise ValueError(
            'steps must be a list like [{"tool": "rgb_colour", "args": {"colour": "blue"}}]'
        )
    con = _db()
    con.execute("INSERT OR REPLACE INTO scenes VALUES (?, ?)", (name, json.dumps(parsed)))
    con.commit()
    return {"saved": name, "steps": len(parsed)}


def delete_scene(name: str) -> dict:
    con = _db()
    con.execute("DELETE FROM scenes WHERE lower(name) = lower(?)", (name,))
    con.commit()
    return {"deleted": name}


def schedule(target: str, when_text: str, args: dict | str | None = None, label: str = "") -> dict:
    """Runs a scene, or any tool with arguments, at a time: 'at 23:00', 'every weekday at 8:45'."""
    w = when.parse(when_text, default_time=None)
    if w.start is None or w.all_day:
        raise ValueError(f"say a time, for example 'every day at 23:00'; got {when_text!r}")
    parsed = json.loads(args) if isinstance(args, str) and args else (args or {})
    con = _db()
    cur = con.execute(
        "INSERT INTO schedules (target, args, at, rrule, label) VALUES (?, ?, ?, ?, ?)",
        (target, json.dumps(parsed), w.start.timestamp(), w.rrule, label or target),
    )
    con.commit()
    return {
        "id": cur.lastrowid,
        "runs": target,
        "at": w.start.strftime("%a %-d %b %H:%M"),
        "repeat": w.rrule,
    }


def schedules() -> list[dict]:
    return [
        {
            "id": r["id"],
            "label": r["label"],
            "runs": r["target"],
            "next": datetime.fromtimestamp(r["at"]).strftime("%a %-d %b %H:%M"),
            "repeat": r["rrule"],
        }
        for r in _db().execute("SELECT * FROM schedules ORDER BY at")
    ]


def unschedule(which: str) -> dict:
    con = _db()
    rows = [
        r
        for r in con.execute("SELECT * FROM schedules")
        if str(r["id"]) == str(which) or str(which).lower() in r["label"].lower()
    ]
    if not rows:
        raise ValueError(f"no schedule matches {which!r}")
    for r in rows:
        con.execute("DELETE FROM schedules WHERE id = ?", (r["id"],))
    con.commit()
    return {"removed": [r["label"] for r in rows]}


EVENTS = ("idle", "usb_added", "offline", "online", "disk_full", "login")


def add_trigger(event: str, target: str, args: dict | str | None = None) -> dict:
    """Runs a scene or tool when an event in `EVENTS` happens."""
    if event not in EVENTS:
        raise ValueError(f"event must be one of {', '.join(EVENTS)}")
    parsed = json.loads(args) if isinstance(args, str) and args else (args or {})
    con = _db()
    cur = con.execute(
        "INSERT INTO triggers (event, target, args) VALUES (?, ?, ?)",
        (event, target, json.dumps(parsed)),
    )
    con.commit()
    return {"id": cur.lastrowid, "when": event, "runs": target}


def triggers() -> list[dict]:
    return [
        {"id": r["id"], "when": r["event"], "runs": r["target"], "args": json.loads(r["args"])}
        for r in _db().execute("SELECT * FROM triggers")
    ]


def remove_trigger(trigger_id: int) -> dict:
    con = _db()
    con.execute("DELETE FROM triggers WHERE id = ?", (int(trigger_id),))
    con.commit()
    return {"removed": int(trigger_id)}


def run_target(target: str, args: dict) -> dict:
    """Runs a scene by name, or else a tool."""
    if target.lower() in {k.lower() for k in scenes()}:
        return run_scene(target)
    return call_tool(target, args)
