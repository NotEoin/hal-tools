"""hal-briefing's tools: morning, evening and job-search briefings assembled from the other modules.

Each part (weather, calendar, tasks, job search, headlines, system health) is
fetched through `halhub.client.call`, so a module that is not installed simply
leaves its part out. The briefing is written as speech, can be sent through
hal-notify and spoken, and is added to the day's note in the vault.
"""

from __future__ import annotations

import logging
from datetime import datetime

from halhub import client
from halkit.config import hal

from .notify import notify
from .settings import settings

log = logging.getLogger(__name__)
CALLER = "briefing"  # the module name the hub checks against `calls`
HUB_TIMEOUT_S = 120.0  # one part may be slow (weather, headlines); the briefing waits no longer


def _hub(tool: str, **args: object) -> object | None:
    """Calls another module's tool through the hub; returns None when it is denied or fails."""
    try:
        return client.call(tool, args, CALLER, timeout=HUB_TIMEOUT_S)
    except (client.ToolDenied, client.ToolFailed) as exc:
        log.warning("briefing part skipped: %s: %s", tool, exc)
        return None


def _weather(day_index: int) -> str | None:
    w = _hub("web_weather", days=2)
    if not isinstance(w, dict):
        return None
    d = w["days"][day_index]
    now = w["now"]
    lead = (
        f"It's {round(now['temperature_c'])} degrees and {now['sky']} now. "
        if day_index == 0
        else ""
    )
    chance = d.get("rain_chance")
    article = "an" if str(chance).startswith("8") or chance in (11, 18) else "a"
    rain = f", with {article} {chance} percent chance of rain" if chance else ""
    when = "Today" if day_index == 0 else "Tomorrow"
    return f"{lead}{when}: {d['sky']}, {round(d['low_c'])} to {round(d['high_c'])} degrees{rain}."


def _agenda(span: str) -> str | None:
    a = _hub("calendar_agenda", span=span)
    if not isinstance(a, dict):
        return None
    ev = a["events"]
    if not ev:
        return f"Nothing in the calendar {span}."
    items = [
        f"{e['title']} at {e['time'].split('-')[0]}"
        if e["time"] != "all day"
        else f"{e['title']} all day"
        for e in ev[:6]
    ]
    return f"{len(ev)} event{'s' * (len(ev) > 1)} {span}: " + "; ".join(items) + "."


def _tasks() -> str | None:
    t = _hub("tasks_list", which="today")
    if not isinstance(t, dict):
        return None
    if not t["tasks"]:
        return "No tasks due."
    overdue = sum(
        1 for x in t["tasks"] if x["due"] and x["due"][:10] < datetime.now().strftime("%Y-%m-%d")
    )
    names = "; ".join(x["title"] for x in t["tasks"][:5])
    return (
        f"{t['count']} task{'s' * (t['count'] > 1)} due"
        + (f", {overdue} overdue" if overdue else "")
        + f": {names}."
    )


def _news() -> str | None:
    n = _hub("web_news", limit=3)
    if not isinstance(n, list) or not n:
        return None
    return "Headlines: " + " ".join(f"{x['title']}." for x in n[:3])


def _health() -> str | None:
    s = _hub("system_overview")
    if not isinstance(s, dict):
        return None
    worries = [
        f"the {d['mount']} disk is {d['use']} full"
        for d in s.get("disks", [])
        if d["use"].rstrip("%").isdigit() and int(d["use"].rstrip("%")) >= 90
    ]
    failed = _hub("system_services")
    if isinstance(failed, dict) and (failed.get("system") or failed.get("user")):
        worries.append(
            f"{len(failed['system']) + len(failed['user'])} background service(s) have failed"
        )
    return ("Computer: " + "; ".join(worries) + ".") if worries else None


def build(kind: str = "morning") -> str:
    """Assembles a morning, evening or job-search briefing and returns its text."""
    name = settings()["name"] or hal()["user_name"] or "there"
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    parts = [f"{greeting}, {name}. It is {datetime.now():%A %-d %B}."]
    if kind == "morning":
        steps = [
            lambda: _weather(0),
            lambda: _agenda("today"),
            _tasks,
            lambda: _hub("jobs_digest"),
            _news,
            _health,
        ]
    elif kind == "jobs":
        steps = [lambda: _hub("jobs_digest")]
    else:
        steps = [
            lambda: _agenda("tomorrow"),
            _tasks,
            lambda: _weather(1),
            lambda: _hub("jobs_digest"),
        ]
    for step in steps:
        text = step()
        if isinstance(text, str) and text:
            # Other modules' summaries open with their own greeting; one is enough.
            parts.append(text.split(". ", 1)[-1] if text.startswith("Good ") else text)
    return " ".join(parts)


def brief(kind: str = "morning", speak: bool = True, push: bool = True, save: bool = True) -> dict:
    """Builds a briefing and delivers it: spoken, pushed to the phone, saved to the daily note."""
    text = build(kind)
    if speak or push:
        notify(f"{kind.title()} briefing", text, speak=speak)
    if save:
        _hub(
            "memory_append",
            note=datetime.now().strftime("%Y-%m-%d"),
            text=f"## {kind.title()} briefing\n\n{text}",
        )
    return {"briefing": text}
