"""Finds the event someone means from loose words: "the pottery class on Friday", "my haircut".

Every tool that takes an `event` goes through resolve(): an exact uid wins; otherwise dates
and times are cut from the words (and used to prefer events on that day), filler such as "my"
or "appointment" is dropped unless the title has it, and the rest is scored by the share of
words found in each title. The best event is chosen only when it is clearly best; otherwise
the error lists the candidates so the assistant can ask which one. Stdlib only.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from . import store, when

FILLER = {"a", "an", "the", "my", "our", "his", "her", "their", "this", "that", "these", "those", "i", "me",
          "event", "events", "appointment", "appointments", "appt", "booking", "entry", "thing", "plan",
          "plans", "calendar", "diary", "on", "at", "in", "for", "of", "to", "with", "and", "please",
          "cancel", "delete", "remove", "move", "reschedule", "one", "next", "this", "coming", "upcoming"}
CLEAR_MARGIN = 0.2      # how far ahead the best must be to be chosen without asking
PAST_DAYS, FUTURE_DAYS = 30, 400

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def stem(word: str) -> str:
    """Reduces a word to a rough stem, so 'classes' meets 'class' and 'haircuts' meets 'haircut'."""
    w = word.lower().replace("'s", "")
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("sses", "shes", "ches", "xes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def words(text: str) -> list[str]:
    return [stem(w) for w in _WORD.findall(text.lower())]


def score(query: list[str], occ: dict) -> float:
    """Returns the share of the query's words found in the event (title words count fully)."""
    title = set(words(occ["title"]))
    other = set(words(f"{occ.get('location', '')} {occ.get('notes', '')}"))
    wanted = [w for w in query if w not in FILLER or w in title]
    if not wanted:
        return 0.0
    hits = 0.0
    for w in wanted:
        if w in title or (len(w) >= 4 and any(t.startswith(w) or w.startswith(t) for t in title if len(t) >= 4)):
            hits += 1
        elif w in other:
            hits += 0.5
    if not hits:
        return 0.0
    # A small nudge for covering more of the title breaks ties between "class" and "pottery class".
    return hits / len(wanted) + 0.1 * len(title & set(wanted)) / max(len(title), 1)


def rank(text: str, now: datetime | None = None, days: int = FUTURE_DAYS) -> list[tuple[float, dict]]:
    """Scores every event occurrence near `now` against `text`; returns one (score, occurrence) per
    event, best first, leaving out events that share no words with it."""
    now = now or datetime.now().replace(second=0, microsecond=0)
    w = when.parse(text, now)
    query = words(w.rest if w.start else text)
    day = w.start.date() if w.start else None
    at = w.start.strftime("%H:%M") if w.start and not w.all_day else None
    best: dict[str, tuple[float, float, dict]] = {}
    for occ in store.between(now - timedelta(days=PAST_DAYS), now + timedelta(days=int(days))):
        s = score(query, occ)
        on_day = day is not None and occ["start"][:10] == day.isoformat()
        if s == 0 and not (on_day and not [q for q in query if q not in FILLER]):
            continue
        if on_day:
            s += 0.5 + (0.25 if at and occ["start"][11:16] == at else 0)
        elif day is not None:
            s -= 0.1
        start = datetime.fromisoformat(occ["start"])
        # Among one event's occurrences prefer the next one, then the most recent.
        nearness = (start - now).total_seconds() if start >= now else 1e12 + (now - start).total_seconds()
        kept = best.get(occ["uid"])
        if kept is None or (s, -nearness) > (kept[0], -kept[1]):
            best[occ["uid"]] = (s, nearness, occ)
    return sorted(((s, o) for s, _, o in best.values()), key=lambda x: (-x[0], x[1]["start"]))


def describe(occ: dict) -> str:
    when_ = "all day" if occ["all_day"] else datetime.fromisoformat(occ["start"]).strftime("%H:%M")
    return f"{occ['title']} ({datetime.fromisoformat(occ['start']):%a %-d %b} {when_}, id {occ['uid']})"


def resolve(event: str, now: datetime | None = None) -> store.Event:
    """Returns the event `event` names, by uid or by its words; raises ValueError naming the
    candidates when none or several fit."""
    e = store.get(str(event).strip())
    if e:
        return e
    ranked = rank(str(event), now)
    if not ranked:
        raise ValueError(f"no event matching {event!r}")
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < CLEAR_MARGIN:
        close = [o for s, o in ranked if ranked[0][0] - s < CLEAR_MARGIN][:5]
        raise ValueError(f"{len(close)} events could be {event!r}: " + "; ".join(describe(o) for o in close)
                         + ". Ask which one, then call again with its id.")
    return store.get(ranked[0][1]["uid"])
