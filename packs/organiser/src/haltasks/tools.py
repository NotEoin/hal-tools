"""hal-tasks' tools: a to-do list in SQLite, mirrored to a note in the vault.

Due dates and repeats are read from plain English. Completing a repeating task
schedules its next occurrence. The vault note (Tasks.md by default) lists open
tasks as Obsidian checkboxes; ticking one there marks it done here on the next
sync, which every tool call runs first.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from . import when
from .config import data_dir, settings, vault

PRIORITY = {"high": 1, "urgent": 1, "normal": 2, "medium": 2, "low": 3}
NAMES = {1: "high", 2: "normal", 3: "low"}


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "tasks.db")
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, notes TEXT,
                   due TEXT, timed INTEGER DEFAULT 0, priority INTEGER DEFAULT 2, tags TEXT, project TEXT,
                   rrule TEXT, created TEXT, done TEXT, reminded INTEGER DEFAULT 0)""")
    return con


def _row(r: sqlite3.Row) -> dict:
    due = r["due"]
    return {"id": r["id"], "title": r["title"], "due": (due[:16].replace("T", " ") if r["timed"] else due[:10]) if due else None,
            "priority": NAMES.get(r["priority"], "normal"), "project": r["project"] or "",
            "tags": [t for t in (r["tags"] or "").split(",") if t], "repeat": r["rrule"],
            "notes": r["notes"] or "", "done": r["done"]}


def _find(con, task: str) -> sqlite3.Row:
    if str(task).isdigit():
        r = con.execute("SELECT * FROM tasks WHERE id = ?", (int(task),)).fetchone()
        if r:
            return r
    words = str(task).lower().split()
    rows = [r for r in con.execute("SELECT * FROM tasks ORDER BY done IS NOT NULL, id DESC")
            if all(w in r["title"].lower() for w in words)]
    if not rows:
        raise ValueError(f"no task matching {task!r}")
    return rows[0]


def add(title: str, due: str = "", priority: str = "normal", tags: list[str] | None = None,
        project: str = "", notes: str = "", repeat: str = "") -> dict:
    """Adds a task; the due date may be in `due` or written into the title."""
    w = when.parse(f"{due} {repeat}".strip()) if (due or repeat) else when.parse(title)
    name = title if (due or repeat) else (w.rest or title) if w.start else title
    con = _db()
    cur = con.execute(
        "INSERT INTO tasks (title, notes, due, timed, priority, tags, project, rrule, created) VALUES (?,?,?,?,?,?,?,?,?)",
        (name.strip(), notes, w.start.isoformat() if w.start else None, int(bool(w.start and not w.all_day)),
         PRIORITY.get(str(priority).lower(), 2), ",".join(tags or []), project, w.rrule,
         datetime.now().isoformat(timespec="seconds")))
    con.commit()
    mirror()
    return {"added": _row(con.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone())}


def list_tasks(which: str = "open", project: str = "", tag: str = "") -> dict:
    """Lists tasks: open, today, overdue, upcoming, done or all, optionally for one project or tag."""
    sync_from_vault()
    con = _db()
    rows = [_row(r) for r in con.execute("SELECT * FROM tasks ORDER BY due IS NULL, due, priority, id")]
    today = date.today().isoformat()
    filters = {
        "open": lambda t: not t["done"],
        "today": lambda t: not t["done"] and t["due"] and t["due"][:10] <= today,
        "overdue": lambda t: not t["done"] and t["due"] and t["due"][:10] < today,
        "upcoming": lambda t: not t["done"] and t["due"] and t["due"][:10] > today,
        "done": lambda t: t["done"] and t["done"][:10] >= (date.today() - timedelta(days=7)).isoformat(),
        "all": lambda t: True,
    }
    keep = filters.get(which, filters["open"])
    out = [t for t in rows if keep(t) and (not project or t["project"].lower() == project.lower())
           and (not tag or tag.lower() in [x.lower() for x in t["tags"]])]
    return {"which": which, "count": len(out), "tasks": out[:50]}


def done(task: str) -> dict:
    """Marks a task done; a repeating task gets its next occurrence."""
    con = _db()
    r = _find(con, task)
    con.execute("UPDATE tasks SET done = ? WHERE id = ?", (datetime.now().isoformat(timespec="seconds"), r["id"]))
    nxt = None
    if r["rrule"] and r["due"]:
        nxt = _next(datetime.fromisoformat(r["due"]), r["rrule"])
        con.execute("INSERT INTO tasks (title, notes, due, timed, priority, tags, project, rrule, created) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (r["title"], r["notes"], nxt.isoformat(), r["timed"], r["priority"],
                                                   r["tags"], r["project"], r["rrule"], datetime.now().isoformat()))
    con.commit()
    mirror()
    return {"done": r["title"], **({"next": nxt.isoformat(timespec="minutes")} if nxt else {})}


def _next(due: datetime, rrule: str) -> datetime:
    rule = dict(p.split("=") for p in rrule.split(";") if "=" in p)
    n = int(rule.get("INTERVAL", 1))
    freq = rule.get("FREQ", "DAILY")
    if freq == "WEEKLY" and "BYDAY" in rule:
        codes = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        days = sorted(codes.index(c) for c in rule["BYDAY"].split(","))
        d = due + timedelta(days=1)
        while d.weekday() not in days:
            d += timedelta(days=1)
        return d
    if freq == "DAILY":
        return due + timedelta(days=n)
    if freq == "WEEKLY":
        return due + timedelta(weeks=n)
    months = n if freq == "MONTHLY" else 12 * n
    m = due.month - 1 + months
    year, month = due.year + m // 12, m % 12 + 1
    for day in (due.day, 30, 29, 28):
        try:
            return due.replace(year=year, month=month, day=day)
        except ValueError:
            continue
    return due


def undo(task: str) -> dict:
    con = _db()
    r = _find(con, task)
    con.execute("UPDATE tasks SET done = NULL WHERE id = ?", (r["id"],))
    con.commit()
    mirror()
    return {"reopened": r["title"]}


def edit(task: str, title: str = "", due: str = "", priority: str = "", project: str = "", notes: str = "") -> dict:
    con = _db()
    r = _find(con, task)
    if title:
        con.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, r["id"]))
    if due:
        w = when.parse(due)
        if w.start is None:
            raise ValueError(f"cannot read the date {due!r}")
        con.execute("UPDATE tasks SET due = ?, timed = ?, reminded = 0 WHERE id = ?",
                    (w.start.isoformat(), int(not w.all_day), r["id"]))
    if priority:
        con.execute("UPDATE tasks SET priority = ? WHERE id = ?", (PRIORITY.get(priority.lower(), 2), r["id"]))
    if project:
        con.execute("UPDATE tasks SET project = ? WHERE id = ?", (project, r["id"]))
    if notes:
        con.execute("UPDATE tasks SET notes = ? WHERE id = ?", (notes, r["id"]))
    con.commit()
    mirror()
    return {"edited": _row(con.execute("SELECT * FROM tasks WHERE id = ?", (r["id"],)).fetchone())}


def delete(task: str) -> dict:
    con = _db()
    r = _find(con, task)
    con.execute("DELETE FROM tasks WHERE id = ?", (r["id"],))
    con.commit()
    mirror()
    return {"deleted": r["title"]}


def projects() -> list[dict]:
    rows = _db().execute("""SELECT project, COUNT(*) n FROM tasks WHERE done IS NULL AND project != ''
                            GROUP BY project ORDER BY n DESC""").fetchall()
    return [{"project": r["project"], "open": r["n"]} for r in rows]


# -- the vault mirror ------------------------------------------------------------

def _note() -> Path:
    return vault() / settings()["vault_note"]


LINE = re.compile(r"^- \[( |x|X)\] .*?<!-- hal-task (\d+) -->\s*$")


def mirror() -> None:
    """Rewrites the vault note listing open tasks, grouped by project, with due dates."""
    note = _note()
    if not note.parent.exists():
        return
    con = _db()
    open_tasks = [_row(r) for r in con.execute("SELECT * FROM tasks WHERE done IS NULL ORDER BY due IS NULL, due, priority")]
    groups: dict[str, list[dict]] = {}
    for t in open_tasks:
        groups.setdefault(t["project"] or "Inbox", []).append(t)
    lines = ["---", "type: tasks", "tags: [tasks]", "hal: generated", "---", "# Tasks", "",
             "Kept by Hal. Tick a box and Hal marks the task done; add tasks by asking Hal.", ""]
    for project in sorted(groups, key=lambda p: (p != "Inbox", p)):
        lines += [f"## {project}" if project == "Inbox" else f"## [[{project}]]", ""]
        for t in groups[project]:
            due = f" (due {t['due']})" if t["due"] else ""
            pri = " !" if t["priority"] == "high" else ""
            lines.append(f"- [ ] {t['title']}{due}{pri} <!-- hal-task {t['id']} -->")
        lines.append("")
    note.write_text("\n".join(lines))


def sync_from_vault() -> int:
    """Marks tasks done that were ticked in the vault note; returns how many."""
    note = _note()
    if not note.exists():
        return 0
    ticked = [int(m.group(2)) for line in note.read_text().splitlines() if (m := LINE.match(line)) and m.group(1) != " "]
    con = _db()
    open_ids = {r[0] for r in con.execute("SELECT id FROM tasks WHERE done IS NULL")}
    for task_id in ticked:
        if task_id in open_ids:
            done(str(task_id))
    return len(ticked)
