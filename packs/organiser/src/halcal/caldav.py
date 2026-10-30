"""Two-way sync with a CalDAV server, such as Apple iCloud Calendar.

Discovery follows RFC 6764: the current user principal, then its calendar home,
then the calendars in it. sync() pulls events in a window around today from the
chosen calendars, pushes local events that are not on the server yet into the
`push_to` calendar, and sends deletions. iCloud needs an app-specific password
from appleid.apple.com, kept in a file, never in config.toml. Stdlib only.
"""

from __future__ import annotations

import base64
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

from . import ics, store
from .settings import settings

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav", "cs": "http://calendarserver.org/ns/"}
PAST_DAYS, FUTURE_DAYS = 30, 400


class CalDAVError(Exception):
    pass


def account() -> dict:
    """Returns the [calendar.caldav] settings with the password read from its file."""
    cfg = settings().get("caldav", {})
    if not cfg.get("url") or not cfg.get("username"):
        raise CalDAVError(
            "CalDAV is not set up; the user connects it by running "
            "`hal-organiser calendar-connect` in a terminal (for iCloud: their Apple ID and an "
            "app-specific password from appleid.apple.com)"
        )
    pw_file = Path(cfg.get("password_file", "~/.config/hal/caldav-password")).expanduser()
    if not pw_file.exists():
        raise CalDAVError(f"no CalDAV password at {pw_file}")
    return {**cfg, "password": pw_file.read_text().strip()}


class Client:
    def __init__(self, url: str, username: str, password: str) -> None:
        self.base = url.rstrip("/") + "/"
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.auth = {"Authorization": f"Basic {token}"}

    def request(
        self,
        method: str,
        url: str,
        body: str = "",
        depth: str | None = None,
        headers: dict | None = None,
    ) -> tuple[int, dict, bytes]:
        h = {**self.auth, "Content-Type": "application/xml; charset=utf-8", **(headers or {})}
        if depth is not None:
            h["Depth"] = depth
        req = urllib.request.Request(  # noqa: S310 - the URL is the user's configured CalDAV server
            urljoin(self.base, url), data=body.encode() if body else None, headers=h, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - same URL as above
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise CalDAVError("the server refused the username or app-specific password") from e
            return e.code, dict(e.headers or {}), e.read()
        except OSError as e:
            raise CalDAVError(f"cannot reach {self.base}: {e}") from e

    def _propfind(self, url: str, props: str, depth: str = "0") -> ET.Element:
        body = f'<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:cs="http://calendarserver.org/ns/"><d:prop>{props}</d:prop></d:propfind>'
        status, _, data = self.request("PROPFIND", url, body, depth)
        if status >= 400:
            raise CalDAVError(f"PROPFIND {url}: HTTP {status}")
        return ET.fromstring(data)  # noqa: S314 - a reply from the user's own CalDAV server; the pack is stdlib only

    def calendars(self) -> list[dict]:
        """Returns the account's event calendars as {name, href, writable}."""
        root = self._propfind(self.base, "<d:current-user-principal/>")
        principal = root.find(".//d:current-user-principal/d:href", NS)
        if principal is None:
            raise CalDAVError("the server did not name a principal")
        root = self._propfind(principal.text, "<c:calendar-home-set/>")
        home_el = root.find(".//c:calendar-home-set/d:href", NS)
        if home_el is None:
            raise CalDAVError("the server did not name a calendar home")
        home = home_el.text
        if home.startswith("http"):
            self.base = home.split("/", 3)[0] + "//" + home.split("/", 3)[2] + "/"
        root = self._propfind(
            home,
            "<d:displayname/><d:resourcetype/><c:supported-calendar-component-set/>"
            "<d:current-user-privilege-set/>",
            "1",
        )
        out = []
        for resp in root.findall("d:response", NS):
            if resp.find(".//d:resourcetype/c:calendar", NS) is None:
                continue
            comps = [
                c.get("name")
                for c in resp.findall(".//c:supported-calendar-component-set/c:comp", NS)
            ]
            if comps and "VEVENT" not in comps:
                continue
            name = resp.find(".//d:displayname", NS)
            href = resp.find("d:href", NS).text
            # Servers that do not list privileges are taken to allow writing.
            privs = {
                p.tag.rsplit("}", 1)[-1]
                for p in resp.findall(".//d:current-user-privilege-set/d:privilege/*", NS)
            }
            # Servers without display names (Radicale) are named by the last part of the path.
            out.append(
                {
                    "name": name.text
                    if name is not None and name.text
                    else href.rstrip("/").rsplit("/", 1)[-1],
                    "href": href,
                    "writable": not privs
                    or bool(privs & {"all", "write", "write-content", "bind"}),
                }
            )
        return out

    def events(self, href: str, start: datetime, end: datetime) -> list[tuple[str, str, str]]:
        """Returns (href, etag, ics) for events overlapping the window."""
        fmt = lambda d: d.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
        body = (
            '<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
            '<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">'
            f'<c:time-range start="{fmt(start)}" end="{fmt(end)}"/>'
            "</c:comp-filter></c:comp-filter></c:filter>"
            f"</c:calendar-query>"
        )
        status, _, data = self.request("REPORT", href, body, "1")
        if status >= 400:
            raise CalDAVError(f"REPORT {href}: HTTP {status}")
        out = []
        for resp in ET.fromstring(data).findall("d:response", NS):  # noqa: S314 - a reply from the user's own CalDAV server; the pack is stdlib only
            cal = resp.find(".//c:calendar-data", NS)
            if cal is not None and cal.text:
                etag = resp.find(".//d:getetag", NS)
                out.append(
                    (resp.find("d:href", NS).text, etag.text if etag is not None else "", cal.text)
                )
        return out

    def put(self, cal_href: str, event: store.Event) -> tuple[str, str]:
        href = cal_href.rstrip("/") + "/" + re.sub(r"[^A-Za-z0-9._-]", "-", event.uid) + ".ics"
        headers = {"Content-Type": "text/calendar; charset=utf-8"}
        headers.update({"If-Match": event.etag} if event.etag else {"If-None-Match": "*"})
        status, h, _ = self.request("PUT", href, ics.calendar([event]), headers=headers)
        if status >= 400:
            raise CalDAVError(f"PUT {href}: HTTP {status}")
        return href, h.get("ETag") or h.get("etag") or ""

    def delete(self, href: str, etag: str = "") -> None:
        status, _, _ = self.request("DELETE", href, headers={"If-Match": etag} if etag else None)
        if status >= 400 and status != 404:
            raise CalDAVError(f"DELETE {href}: HTTP {status}")


def client() -> Client:
    a = account()
    return Client(a["url"], a["username"], a["password"])


def sync() -> dict:
    """Pulls, pushes and deletes against the configured CalDAV account; returns counts."""
    cfg = settings().get("caldav", {})
    c = client()
    cals = c.calendars()
    wanted = {w.lower() for w in (cfg.get("calendars") or [x["name"] for x in cals])}
    push_to = cfg.get("push_to") or (cals[0]["name"] if cals else None)
    now = datetime.now(UTC)
    pulled = pushed = deleted = 0
    con = store.db()
    # Deletions go first, so a deleted event is not pulled straight back from the server.
    for r in con.execute("SELECT uid, href, etag FROM events WHERE deleted = 1").fetchall():
        if r["href"]:
            c.delete(r["href"], r["etag"])
            deleted += 1
        con.execute("DELETE FROM events WHERE uid = ?", (r["uid"],))
    con.commit()
    for cal in cals:
        if cal["name"].lower() not in wanted:
            continue
        seen = set()
        for href, etag, text in c.events(
            cal["href"], now - timedelta(days=PAST_DAYS), now + timedelta(days=FUTURE_DAYS)
        ):
            for ev in ics.parse(text, calendar=f"caldav:{cal['name']}"):
                ev.href, ev.etag = href, etag
                existing = store.get(ev.uid)
                if existing is None or existing.etag != etag:
                    store.save(ev, dirty=False)
                    pulled += 1
                seen.add(ev.uid)
        # Events gone from the server are gone here too, unless they lie outside the window.
        lo = (now - timedelta(days=PAST_DAYS)).replace(tzinfo=None).isoformat()
        for (uid,) in con.execute(
            "SELECT uid FROM events WHERE calendar = ? AND deleted = 0 AND rrule IS NULL "
            "AND start >= ?",
            (f"caldav:{cal['name']}", lo),
        ).fetchall():
            if uid not in seen:
                con.execute("DELETE FROM events WHERE uid = ?", (uid,))
    con.commit()
    want = (push_to or "").lower()
    target = next(
        (
            x
            for x in cals
            if want in (x["name"].lower(), x["href"].rstrip("/").rsplit("/", 1)[-1].lower())
        ),
        None,
    )
    for e in store.dirty():
        if e.href:
            cal_href = e.href.rsplit("/", 1)[0]
        elif e.calendar == "local" and target:
            cal_href = target["href"]
            e.calendar = f"caldav:{target['name']}"
        else:
            continue
        e.href, e.etag = c.put(cal_href, e)
        store.save(e, dirty=False)
        pushed += 1
    return {
        "calendars": [x["name"] for x in cals],
        "pulled": pulled,
        "pushed": pushed,
        "deleted": deleted,
    }
