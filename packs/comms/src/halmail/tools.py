"""hal-mail's tools: read, search and summarise email over IMAP; draft and send replies.

Mailboxes are opened read-only (EXAMINE, BODY.PEEK), so reading never marks
mail as read. Drafts are appended to the account's Drafts folder for you to
review; sending through SMTP needs confirmation through hal-hub. Passwords are
app passwords kept in files named in the config, never in the config itself.
"""
from __future__ import annotations

import email
import email.header
import email.utils
import html
import imaplib
import re
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from . import llm
from .config import settings

DRAFTS = {"imap.gmail.com": '"[Gmail]/Drafts"'}


def _account(name: str = "") -> dict:
    accounts = settings()["accounts"]
    key = name or settings()["default"]
    if key not in accounts:
        raise ValueError(f"no mail account {key!r}; have {', '.join(accounts)}")
    a = dict(accounts[key])
    pw = Path(a["password_file"]).expanduser()
    if not pw.exists():
        raise RuntimeError(f"no password file at {pw}; create an app password for {a['address']}")
    a["password"] = pw.read_text().strip().replace(" ", "")
    return a


def _connect(a: dict) -> imaplib.IMAP4_SSL:
    m = imaplib.IMAP4_SSL(a.get("imap", "imap.gmail.com"))
    m.login(a["address"], a["password"])
    return m


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        text = str(email.header.make_header(email.header.decode_header(value)))
    except (LookupError, UnicodeDecodeError):
        text = value
    return re.sub(r"\s+", " ", text).strip()


def _body(msg: email.message.Message) -> str:
    plain, rich = "", ""
    for part in msg.walk() if msg.is_multipart() else [msg]:
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        payload = part.get_payload(decode=True) or b""
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and not plain:
            plain = text
        elif ctype == "text/html" and not rich:
            rich = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", "", text)))
    return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", plain or rich)).strip()


def _summary(uid: bytes, msg: email.message.Message) -> dict:
    return {"id": uid.decode(), "from": _decode(msg.get("From")), "subject": _decode(msg.get("Subject")),
            "date": email.utils.parsedate_to_datetime(msg["Date"]).strftime("%a %-d %b %H:%M") if msg.get("Date") else ""}


def _fetch(m: imaplib.IMAP4_SSL, uids: list[bytes], headers_only: bool = True) -> list[tuple[bytes, email.message.Message]]:
    out = []
    part = "BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]" if headers_only else "BODY.PEEK[]"
    for uid in uids:
        typ, data = m.uid("FETCH", uid, f"({part})")
        if typ == "OK" and data and isinstance(data[0], tuple):
            out.append((uid, email.message_from_bytes(data[0][1])))
    return out


def unread(account: str = "", limit: int = 10) -> dict:
    """Unread messages in the inbox, newest first."""
    a = _account(account)
    m = _connect(a)
    try:
        m.select("INBOX", readonly=True)
        _, data = m.uid("SEARCH", None, "UNSEEN")
        uids = data[0].split()[-int(limit):][::-1]
        return {"account": a["address"], "unread": len(data[0].split()),
                "messages": [_summary(u, msg) for u, msg in _fetch(m, uids)]}
    finally:
        m.logout()


def search(query: str, account: str = "", days: int = 30, limit: int = 10) -> list[dict]:
    """Messages from the last N days whose sender, subject or text contains the words."""
    a = _account(account)
    m = _connect(a)
    try:
        m.select("INBOX", readonly=True)
        since = (datetime.now() - timedelta(days=int(days))).strftime("%d-%b-%Y")
        crit = ["SINCE", since] + [x for w in query.split() for x in ("TEXT", f'"{w}"')]
        _, data = m.uid("SEARCH", None, *crit)
        uids = data[0].split()[-int(limit):][::-1]
        return [_summary(u, msg) for u, msg in _fetch(m, uids)]
    finally:
        m.logout()


def read(message_id: str, account: str = "") -> dict:
    """The full text of one message, by the id from unread or search."""
    a = _account(account)
    m = _connect(a)
    try:
        m.select("INBOX", readonly=True)
        got = _fetch(m, [message_id.encode()], headers_only=False)
        if not got:
            raise ValueError(f"no message {message_id}")
        uid, msg = got[0]
        return {**_summary(uid, msg), "to": _decode(msg.get("To")), "text": _body(msg)[:8000],
                "message_id": msg.get("Message-ID")}
    finally:
        m.logout()


def summarise(account: str = "", limit: int = 15) -> dict:
    """A short spoken summary of the unread mail: who wrote, what needs a reply."""
    u = unread(account, limit)
    if not u["messages"]:
        return {"summary": "No unread mail."}
    listing = "\n".join(f"- {x['from']}: {x['subject']}" for x in u["messages"])
    text = llm.chat("Summarise this list of unread emails for the owner in at most 80 words of plain speech. "
                    "Group newsletters and notifications together; name people who wrote personally and anything "
                    "that needs a reply or action.", listing)
    return {"unread": u["unread"], "summary": text.strip()}


def _message(a: dict, to: str, subject: str, body: str, reply_to: str = "") -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = a["address"], to, subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    if reply_to:
        msg["In-Reply-To"] = msg["References"] = reply_to
    msg.set_content(body)
    return msg


def draft(to: str, subject: str, body: str, account: str = "", reply_to: str = "") -> dict:
    """Saves an email in the Drafts folder for you to check and send yourself."""
    a = _account(account)
    msg = _message(a, to, subject, body, reply_to)
    m = _connect(a)
    try:
        folder = a.get("drafts") or DRAFTS.get(a.get("imap", "imap.gmail.com"), "Drafts")
        typ, data = m.append(folder, r"(\Draft)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        if typ != "OK":
            raise RuntimeError(f"could not save the draft: {data}")
        return {"saved_draft": subject, "to": to, "folder": folder}
    finally:
        m.logout()


def send(to: str, subject: str, body: str, account: str = "", reply_to: str = "") -> dict:
    """Sends an email now."""
    a = _account(account)
    msg = _message(a, to, subject, body, reply_to)
    with smtplib.SMTP_SSL(a.get("smtp", "smtp.gmail.com"), 465, timeout=30) as s:
        s.login(a["address"], a["password"])
        s.send_message(msg)
    return {"sent": subject, "to": to}


def accounts() -> list[str]:
    return [f"{k}: {v['address']}" for k, v in settings()["accounts"].items()]
