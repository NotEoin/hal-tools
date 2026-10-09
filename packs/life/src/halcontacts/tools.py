"""hal-contacts' tools: the people in your life, kept as notes in the vault's People folder.

Each person is People/<Name>.md with frontmatter (email, phone, birthday,
relationship, last_contact) and a dated log of interactions, so hal-memory's
links and searches reach them too. A birthday is added to the calendar as a
yearly event through hal-hub when it is installed.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import settings, vault

FIELDS = ("email", "phone", "birthday", "relationship", "company", "address", "last_contact")
FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def _dir() -> Path:
    d = vault() / settings()["folder"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(name: str) -> str:
    return re.sub(r'[*"\\/<>:|?#^\[\]]', " ", name).strip()


def _read(p: Path) -> tuple[dict, str]:
    text = p.read_text(errors="ignore")
    m = FRONT.match(text)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip() and v.strip():
                meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end():] if m else text


def _write(p: Path, meta: dict, body: str) -> None:
    lines = [f'{k}: "{v}"' if re.search(r"[:#]", str(v)) else f"{k}: {v}" for k, v in meta.items() if v not in ("", None)]
    p.write_text("---\n" + "\n".join(lines) + "\n---\n" + body.lstrip("\n"))


def _find(name: str) -> Path:
    exact = _dir() / f"{_slug(name)}.md"
    if exact.exists():
        return exact
    words = name.lower().split()
    hits = [p for p in _dir().glob("*.md") if all(w in p.stem.lower() for w in words)]
    if not hits:
        raise ValueError(f"no contact called {name!r}")
    return hits[0]


def _hub(tool: str, args: dict) -> None:
    exe = shutil.which("hal-hub")
    if exe:
        subprocess.run([exe, "call", tool, "--json", json.dumps(args)], capture_output=True, timeout=60)


def _birthday(text: str) -> str:
    """Normalises '3 March', '1999-03-03' or '03/03' to MM-DD or YYYY-MM-DD."""
    t = text.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{2}", t):
        return t
    for fmt in ("%d %B", "%d %b", "%B %d", "%b %d", "%d/%m", "%d %B %Y", "%d %b %Y", "%d/%m/%Y"):
        try:
            d = datetime.strptime(re.sub(r"(st|nd|rd|th)\b", "", t), fmt)
            return d.strftime("%Y-%m-%d" if "%Y" in fmt else "%m-%d")
        except ValueError:
            continue
    raise ValueError(f"cannot read the birthday {text!r}; try '3 March' or 1999-03-03")


def add(name: str, email: str = "", phone: str = "", birthday: str = "", relationship: str = "",
        company: str = "", notes: str = "") -> dict:
    """Adds a person (or fills in details for one who exists)."""
    p = _dir() / f"{_slug(name)}.md"
    meta, body = _read(p) if p.exists() else ({"type": "person", "tags": "[person]"}, f"# {name}\n\n## Log\n\n")
    for k, v in (("email", email), ("phone", phone), ("relationship", relationship), ("company", company)):
        if v:
            meta[k] = v
    if birthday:
        meta["birthday"] = _birthday(birthday)
        md = meta["birthday"][-5:]
        _hub("calendar_add", {"title": f"{name}'s birthday",
                              "when_text": datetime.strptime(md, "%m-%d").strftime("%-d %B") + " every year"})
    if notes:
        body = body.replace("## Log\n", f"{notes.strip()}\n\n## Log\n", 1) if "## Log" in body else body + notes
    _write(p, meta, body)
    return {"saved": p.stem, "path": str(p)}


def get(name: str) -> dict:
    p = _find(name)
    meta, body = _read(p)
    return {"name": p.stem, **{k: meta.get(k) for k in FIELDS if meta.get(k)}, "notes": body.strip()[:3000]}


def find(query: str) -> list[dict]:
    """People whose name, details or notes mention the words."""
    words = query.lower().split()
    out = []
    for p in sorted(_dir().glob("*.md")):
        text = p.read_text(errors="ignore").lower()
        if all(w in text or w in p.stem.lower() for w in words):
            meta, _ = _read(p)
            out.append({"name": p.stem, **{k: meta.get(k) for k in ("email", "phone", "relationship") if meta.get(k)}})
    return out[:25]


def log(name: str, note: str, when: str = "") -> dict:
    """Records an interaction ('had coffee, she's moving to Leeds') and updates when you last spoke."""
    p = _find(name)
    meta, body = _read(p)
    day = when or date.today().isoformat()
    meta["last_contact"] = day
    if "## Log" not in body:
        body = body.rstrip() + "\n\n## Log\n\n"
    body = body.rstrip() + f"\n- {day}: {note.strip()}\n"
    _write(p, meta, body)
    return {"logged": p.stem, "date": day}


def birthdays(days: int = 30) -> list[dict]:
    """Birthdays in the next N days, soonest first, with the age where the year is known."""
    today = date.today()
    out = []
    for p in _dir().glob("*.md"):
        b = _read(p)[0].get("birthday")
        if not b:
            continue
        month, day = int(b[-5:-3]), int(b[-2:])
        nxt = date(today.year, month, day)
        if nxt < today:
            nxt = date(today.year + 1, month, day)
        gap = (nxt - today).days
        if gap <= int(days):
            age = nxt.year - int(b[:4]) if len(b) == 10 else None
            out.append({"name": p.stem, "date": nxt.strftime("%a %-d %b"), "in_days": gap, "turning": age})
    return sorted(out, key=lambda x: x["in_days"])


def stale(days: int = 60) -> list[dict]:
    """People you have not been in touch with for N days (those with a recorded last contact)."""
    cutoff = (date.today() - timedelta(days=int(days))).isoformat()
    out = []
    for p in _dir().glob("*.md"):
        last = _read(p)[0].get("last_contact")
        if last and last < cutoff:
            out.append({"name": p.stem, "last_contact": last})
    return sorted(out, key=lambda x: x["last_contact"])


def import_vcard(path: str) -> dict:
    """Imports contacts from a .vcf file (exported from a phone, Google or iCloud)."""
    text = re.sub(r"\r?\n[ \t]", "", Path(path).expanduser().read_text(errors="ignore"))
    count = 0
    for card in re.findall(r"BEGIN:VCARD(.*?)END:VCARD", text, re.S):
        get = lambda key: next((l.split(":", 1)[1].strip() for l in card.splitlines()  # noqa: E731
                                if l.upper().startswith(key) and ":" in l), "")
        name = get("FN")
        if not name:
            continue
        bday = get("BDAY").replace("--", "")
        if re.fullmatch(r"\d{8}", bday):
            bday = f"{bday[:4]}-{bday[4:6]}-{bday[6:]}"
        elif re.fullmatch(r"\d{4}", bday):
            bday = f"{bday[:2]}-{bday[2:]}"
        try:
            add(name, email=get("EMAIL"), phone=get("TEL"), birthday=bday if bday else "", company=get("ORG"))
        except ValueError:
            add(name, email=get("EMAIL"), phone=get("TEL"), company=get("ORG"))
        count += 1
    return {"imported": count}
