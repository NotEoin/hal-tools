"""hal-feeds' tools: a read-later list and RSS or Atom subscriptions.

Saved links get their title and, when asked, a summary from the local model.
Feeds are polled on demand; items seen are remembered so "what's new" only
lists unread ones. Stdlib only.
"""

from __future__ import annotations

import html
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

from hal_online import net
from halkit import llm as halkit_llm

from .settings import data_dir

MODEL_TIMEOUT_S = 300.0  # a local model on a cold start can take minutes to answer


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "feeds.db")
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS later (
            url TEXT PRIMARY KEY, title TEXT, summary TEXT, added TEXT, read TEXT);
        CREATE TABLE IF NOT EXISTS feeds (url TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS items (
            link TEXT PRIMARY KEY, feed TEXT, title TEXT, summary TEXT, seen TEXT,
            read INTEGER DEFAULT 0);
    """)
    return con


_get = net.get


def _strip(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def save(url: str, summarise: bool = False) -> dict:
    """Saves a link to read later, with its title (and a summary if asked)."""
    page = _get(url).decode(errors="ignore")
    m = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = _strip(m.group(1)) if m else url
    summary = ""
    if summarise:
        text = re.sub(
            r"\s+", " ", _strip(re.sub(r"(?is)<(script|style|nav|footer).*?</\1>", "", page))
        )
        summary = halkit_llm.chat(
            [
                {
                    "role": "system",
                    "content": "Summarise this web page in at most 60 words. Use only the page.",
                },
                {"role": "user", "content": text[:10000]},
            ],
            timeout=MODEL_TIMEOUT_S,
        ).strip()
    con = _db()
    con.execute(
        "INSERT OR REPLACE INTO later VALUES (?, ?, ?, ?, NULL)",
        (url, title, summary, datetime.now().isoformat()),
    )
    con.commit()
    return {"saved": title, "summary": summary or None}


def reading_list(include_read: bool = False) -> list[dict]:
    """Returns the saved reading list, unread items only unless `include_read` is set."""
    sql = (
        "SELECT * FROM later"  # noqa: S608 - fixed fragments only
        + ("" if include_read else " WHERE read IS NULL")
        + " ORDER BY added DESC"
    )
    return [
        {"title": r["title"], "url": r["url"], "summary": r["summary"], "added": r["added"][:10]}
        for r in _db().execute(sql)
    ]


def mark_read(item: str) -> dict:
    """Marks a saved link or feed item read, by URL or words in its title."""
    con = _db()
    n = con.execute(
        "UPDATE later SET read = ? WHERE url = ? OR title LIKE ?",
        (datetime.now().isoformat(), item, f"%{item}%"),
    ).rowcount
    n += con.execute(
        "UPDATE items SET read = 1 WHERE link = ? OR title LIKE ?", (item, f"%{item}%")
    ).rowcount
    con.commit()
    return {"marked": n}


def subscribe(url: str, name: str = "") -> dict:
    """Subscribes to an RSS or Atom feed."""
    root = net.parse_xml(_get(url))
    title = next((c.text for c in root.iter() if c.tag.split("}")[-1] == "title" and c.text), url)
    con = _db()
    con.execute("INSERT OR REPLACE INTO feeds VALUES (?, ?)", (url, name or title.strip()))
    con.commit()
    refresh()
    return {"subscribed": name or title.strip()}


def unsubscribe(name: str) -> dict:
    """Removes the feeds whose name or URL matches."""
    con = _db()
    n = con.execute("DELETE FROM feeds WHERE name LIKE ? OR url = ?", (f"%{name}%", name)).rowcount
    con.commit()
    return {"removed": n}


def feeds() -> list[dict]:
    """Returns the subscribed feeds."""
    con = _db()
    return [
        {
            "name": r["name"],
            "url": r["url"],
            "unread": con.execute(
                "SELECT COUNT(*) FROM items WHERE feed = ? AND read = 0", (r["url"],)
            ).fetchone()[0],
        }
        for r in con.execute("SELECT * FROM feeds ORDER BY name")
    ]


def refresh() -> dict:
    """Fetches every feed and stores new items."""
    con = _db()
    new = 0
    for f in con.execute("SELECT * FROM feeds").fetchall():
        try:
            root = net.parse_xml(_get(f["url"]))
        except (OSError, ValueError, ET.ParseError):  # ValueError: BlockedURL
            continue
        for it in root.iter():
            if it.tag.split("}")[-1] not in ("item", "entry"):
                continue
            kids = {c.tag.split("}")[-1]: c for c in it}
            link = kids.get("link")
            href = (link.text or link.get("href") or "") if link is not None else ""
            title = _strip(kids["title"].text) if "title" in kids else href
            # An element with no children is falsy, so pick the first present one explicitly.
            body = next((kids[k] for k in ("description", "summary", "content") if k in kids), None)
            summ = _strip(body.text if body is not None else "")
            new += con.execute(
                "INSERT OR IGNORE INTO items (link, feed, title, summary, seen)"
                " VALUES (?, ?, ?, ?, ?)",
                (href or title, f["url"], title, summ[:400], datetime.now().isoformat()),
            ).rowcount
    con.commit()
    return {"new_items": new}


def whats_new(limit: int = 15, feed: str = "") -> list[dict]:
    """Unread items across subscriptions, newest first."""
    refresh()
    con = _db()
    names = {r["url"]: r["name"] for r in con.execute("SELECT * FROM feeds")}
    rows = con.execute(
        "SELECT * FROM items WHERE read = 0 ORDER BY seen DESC LIMIT ?", (int(limit) * 4,)
    ).fetchall()
    out = [
        {
            "feed": names.get(r["feed"], ""),
            "title": r["title"],
            "link": r["link"],
            "summary": r["summary"][:200],
        }
        for r in rows
        if not feed or feed.lower() in names.get(r["feed"], "").lower()
    ]
    return out[: int(limit)]
