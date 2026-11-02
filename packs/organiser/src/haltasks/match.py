"""Finds the task someone means from loose words: "I've bought the batteries" is "Buy batteries".

An id ("3", "#3", "task 3") is taken exactly. Otherwise dates are cut from the words, filler
("I've", "the", "tick off") is dropped unless the title has it, and words are compared by a
light stem, so "bought" meets "buy" and "batteries" meets "battery". The best task is chosen
only when it is clearly best; otherwise the error lists the candidates. Stdlib only.
"""

from __future__ import annotations

import re

from halkit import when

# Past tenses and other forms people use when reporting a task done.
IRREGULAR = {
    "bought": "buy",
    "brought": "bring",
    "paid": "pay",
    "sent": "send",
    "made": "make",
    "went": "go",
    "gone": "go",
    "did": "do",
    "done": "do",
    "rang": "ring",
    "rung": "ring",
    "took": "take",
    "taken": "take",
    "got": "get",
    "gotten": "get",
    "wrote": "write",
    "written": "write",
    "sold": "sell",
    "told": "tell",
    "found": "find",
    "put": "put",
    "read": "read",
    "left": "leave",
    "met": "meet",
    "kept": "keep",
    "spoke": "speak",
    "spoken": "speak",
    "gave": "give",
    "given": "give",
    "saw": "see",
    "seen": "see",
    "drove": "drive",
    "driven": "drive",
    "ate": "eat",
    "eaten": "eat",
    "fed": "feed",
    "hung": "hang",
    "swept": "sweep",
    "booked": "book",
    "children": "child",
    "people": "person",
}
FILLER = {
    "i",
    "ive",
    "i've",
    "im",
    "i'm",
    "i'd",
    "id",
    "have",
    "has",
    "had",
    "just",
    "already",
    "finally",
    "now",
    "the",
    "a",
    "an",
    "my",
    "our",
    "some",
    "that",
    "this",
    "it",
    "its",
    "those",
    "these",
    "them",
    "task",
    "tasks",
    "todo",
    "to",
    "do",
    "item",
    "list",
    "tick",
    "ticked",
    "ticking",
    "off",
    "mark",
    "marked",
    "as",
    "done",
    "finished",
    "complete",
    "completed",
    "please",
    "can",
    "you",
    "for",
    "of",
    "on",
    "in",
    "at",
    "and",
    "is",
    "was",
    "all",
    "been",
    "got",
}
CLEAR_MARGIN = 0.2
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_DOUBLE = re.compile(r"([bdgmnpt])\1$")


def stem(word: str) -> str:
    """Reduces a word to a rough stem: 'bought' and 'buying' to 'buy', 'batteries' to 'battery'."""
    w = word.lower().replace("'s", "")
    if w in IRREGULAR:
        w = IRREGULAR[w]
    elif len(w) > 4 and w.endswith(("ies", "ied")):
        w = w[:-3] + "y"
    elif (len(w) > 5 and w.endswith("ing")) or (len(w) > 3 and w.endswith("ed")):
        w = w[:-3] if w.endswith("ing") else w[:-2]
        if len(w) > 3 and _DOUBLE.search(w):  # "running" -> "run", but "adding" -> "add"
            w = w[:-1]
    elif len(w) > 4 and w.endswith(("sses", "shes", "ches", "xes")):
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    if len(w) > 2 and w.endswith("e"):
        w = w[:-1]
    return w


def words(text: str) -> list[str]:
    """Returns the stemmed words of a text."""
    return [stem(w) for w in _WORD.findall(text.lower())]


def score(query: list[str], title: str) -> float:
    """Returns the share of the query's (non-filler) words found in the title."""
    have = set(words(title))
    wanted = [w for w in query if w not in {stem(f) for f in FILLER} or w in have]
    if not wanted:
        return 0.0
    hits = sum(
        1
        for w in wanted
        if w in have
        or (len(w) >= 4 and any(h.startswith(w) or w.startswith(h) for h in have if len(h) >= 4))
    )
    if not hits:
        return 0.0
    # A nudge for covering more of the title breaks ties between "milk" and "buy milk".
    return hits / len(wanted) + 0.1 * len(have & set(wanted)) / max(len(have), 1)


def query_words(task: str) -> list[str]:
    """The words of `task` with any date or time phrase cut out."""
    w = when.parse(task)
    return words(w.rest if w.start and w.rest else task)


def task_id(task: str) -> int | None:
    """Returns the number in a phrase such as "task 4", or None."""
    m = re.fullmatch(r"\s*(?:task|to-?do|item|number|no\.?)?\s*#?\s*(\d+)\s*", str(task), re.I)
    return int(m[1]) if m else None


def best(task: str, rows: list, prefer_open: bool = True):
    """Picks the row `task` means from rows with 'id', 'title' and 'done'; raises ValueError
    naming the candidates when none or several fit."""
    q = query_words(task)
    scored = [(s, r) for r in rows if (s := score(q, r["title"])) > 0]
    # Open tasks are meant when completing or editing, done ones when reopening: a done
    # "Buy batteries" from last week does not compete with today's open one.
    preferred = [(s, r) for s, r in scored if bool(r["done"]) != prefer_open]
    scored = preferred or scored
    scored.sort(key=lambda x: (-x[0], -x[1]["id"]))
    if not scored:
        raise ValueError(f"no task matching {task!r}")
    close = [r for s, r in scored if scored[0][0] - s < CLEAR_MARGIN]
    if len({r["title"].strip().lower() for r in close}) == 1:
        # Copies of one task are interchangeable: take the newest, or the last one completed.
        return max(close, key=lambda r: (r["done"] or "", r["id"]))
    close = close[:5]
    raise ValueError(
        f"{len(close)} tasks could be {task!r}: "
        + "; ".join(f"#{r['id']} {r['title']}" + (" (done)" if r["done"] else "") for r in close)
        + ". Ask which one, then call again with its id."
    )
