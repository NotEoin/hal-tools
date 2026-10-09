"""hal-routines' tools: scenes, schedules and triggers built from other modules' tools.

A scene is a named list of tool calls run through hal-hub, such as "focus":
do-not-disturb for an hour, warm lights, music paused. Schedules run a scene or
a single tool at a time, once or repeating; triggers run one when something
happens. The daemon (python -m halroutines.daemon) runs schedules and triggers.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime

from . import when
from .config import data_dir, settings


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "routines.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS scenes (name TEXT PRIMARY KEY, steps TEXT);
        CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY, target TEXT, args TEXT, at REAL,
            rrule TEXT, label TEXT);
        CREATE TABLE IF NOT EXISTS triggers (id INTEGER PRIMARY KEY, event TEXT, target TEXT, args TEXT,
            last REAL DEFAULT 0);
    """)
    return con


def call_tool(tool: str, args: dict | None = None) -> dict:
    """Runs one tool through the hal-hub command; returns its JSON result or error."""
    exe = shutil.which("hal-hub")
    if not exe:
        return {"error": "hal-hub is not installed"}
    payload = json.dumps({**(args or {}), "_confirmed": True})
    done = subprocess.run([exe, "call", tool, "--json", payload], capture_output=True, text=True, timeout=600)
    try:
        return json.loads(done.stdout) if done.stdout.strip() else {"error": done.stderr.strip()[-300:]}
    except json.JSONDecodeError:
        return {"result": done.stdout.strip()}


def scenes() -> dict:
    """Every scene, the built-in ones from config and those saved by asking Hal."""
    out = dict(settings()["scenes"])
    for r in _db().execute("SELECT * FROM scenes"):
        out[r["name"]] = json.loads(r["steps"])
    return out


def run_scene(name: str) -> dict:
    """Runs every step of a scene in order; a failing step does not stop the rest."""
    all_scenes = scenes()
    key = next((k for k in all_scenes if k.lower() == name.lower()), None)
    if key is None:
        raise ValueError(f"no scene {name!r}; have {', '.join(all_scenes)}")
    results = []
    for step in all_scenes[key]:
        out = call_tool(step["tool"], step.get("args"))
        results.append({"tool": step["tool"], "ok": "error" not in out})
    return {"scene": key, "steps": results}


def save_scene(name: str, steps: list | str) -> dict:
    """Saves a scene: a list of {"tool": ..., "args": {...}} steps."""
    parsed = json.loads(steps) if isinstance(steps, str) else steps
    if not isinstance(parsed, list) or not all(isinstance(s, dict) and "tool" in s for s in parsed):
        raise ValueError('steps must be a list like [{"tool": "rgb_colour", "args": {"colour": "blue"}}]')
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
    cur = con.execute("INSERT INTO schedules (target, args, at, rrule, label) VALUES (?, ?, ?, ?, ?)",
                      (target, json.dumps(parsed), w.start.timestamp(), w.rrule, label or target))
    con.commit()
    return {"id": cur.lastrowid, "runs": target, "at": w.start.strftime("%a %-d %b %H:%M"), "repeat": w.rrule}


def schedules() -> list[dict]:
    return [{"id": r["id"], "label": r["label"], "runs": r["target"],
             "next": datetime.fromtimestamp(r["at"]).strftime("%a %-d %b %H:%M"), "repeat": r["rrule"]}
            for r in _db().execute("SELECT * FROM schedules ORDER BY at")]


def unschedule(which: str) -> dict:
    con = _db()
    rows = [r for r in con.execute("SELECT * FROM schedules")
            if str(r["id"]) == str(which) or str(which).lower() in r["label"].lower()]
    if not rows:
        raise ValueError(f"no schedule matches {which!r}")
    for r in rows:
        con.execute("DELETE FROM schedules WHERE id = ?", (r["id"],))
    con.commit()
    return {"removed": [r["label"] for r in rows]}


EVENTS = ("idle", "usb_added", "offline", "online", "disk_full", "login")


def add_trigger(event: str, target: str, args: dict | str | None = None) -> dict:
    """Runs a scene or tool when something happens: idle, usb_added, offline, online, disk_full or login."""
    if event not in EVENTS:
        raise ValueError(f"event must be one of {', '.join(EVENTS)}")
    parsed = json.loads(args) if isinstance(args, str) and args else (args or {})
    con = _db()
    cur = con.execute("INSERT INTO triggers (event, target, args) VALUES (?, ?, ?)", (event, target, json.dumps(parsed)))
    con.commit()
    return {"id": cur.lastrowid, "when": event, "runs": target}


def triggers() -> list[dict]:
    return [{"id": r["id"], "when": r["event"], "runs": r["target"], "args": json.loads(r["args"])}
            for r in _db().execute("SELECT * FROM triggers")]


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
