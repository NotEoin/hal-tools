"""hal-notify's tools: send an alert everywhere it should go, honouring quiet hours and do-not-disturb.

Channels: ntfy phone push, the desktop's notification daemon, HAL's voice
(hal-voice's hal-say) and Telegram (the token and chat that hal-telegram pairs).
Every alert is kept in a history table. Stdlib only.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from .config import data_dir, settings

TELEGRAM_DIR = Path("~/.config/hal").expanduser()
# hal-voice's speaker, beside this module in the ecosystem's extensions folder.
HAL_SAY = Path(__file__).resolve().parents[2] / "hal-voice" / "bin" / "hal-say"


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(data_dir() / "history.db")
    con.execute(
        "CREATE TABLE IF NOT EXISTS sent (at TEXT, title TEXT, body TEXT, urgent INTEGER, channels TEXT)"
    )
    return con


def _dnd_until() -> datetime | None:
    f = data_dir() / "dnd"
    if not f.exists():
        return None
    until = datetime.fromisoformat(f.read_text().strip())
    if until < datetime.now():
        f.unlink()
        return None
    return until


def quiet() -> bool:
    """True during quiet hours or while do-not-disturb is on."""
    cfg = settings()
    hour = datetime.now().hour
    start, end = int(cfg.get("quiet_from", 22)), int(cfg.get("quiet_until", 8))
    in_hours = (hour >= start or hour < end) if start > end else start <= hour < end
    return in_hours or _dnd_until() is not None


def _desktop(title: str, body: str, urgent: bool) -> bool:
    try:
        return (
            subprocess.run(
                ["notify-send", "-a", "Hal", *(["-u", "critical"] if urgent else []), title, body],
                timeout=5,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def _ntfy(title: str, body: str, urgent: bool, silent: bool, url: str = "") -> bool:
    topic = settings().get("ntfy_topic")
    if not topic:
        return False
    headers = {"Title": title.encode(), "Tags": "robot"}
    headers["Priority"] = "high" if urgent else ("min" if silent else "default")
    if url:
        headers["Click"] = url
    server = settings().get("ntfy_server", "https://ntfy.sh").rstrip("/")
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"{server}/{topic}", data=body.encode(), headers=headers),
            timeout=10,
        )
        return True
    except OSError:
        return False


def _speak(title: str, body: str) -> bool:
    say = shutil.which("hal-say") or str(HAL_SAY)
    if not Path(say).exists():
        return False
    try:
        subprocess.Popen(
            [say, f"{title}. {body}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except OSError:
        return False


def _telegram(title: str, body: str) -> bool:
    token_file, chat_file = TELEGRAM_DIR / "telegram-token", TELEGRAM_DIR / "telegram-chat"
    if not (token_file.exists() and chat_file.exists()):
        return False
    data = urllib.parse.urlencode(
        {"chat_id": chat_file.read_text().strip(), "text": f"{title}\n{body}"}
    ).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token_file.read_text().strip()}/sendMessage",
            data=data,
            timeout=10,
        )
        return True
    except OSError:
        return False


def send(
    title: str,
    body: str = "",
    urgent: bool = False,
    speak: bool = False,
    channels: list[str] | None = None,
    url: str = "",
) -> dict:
    """Sends an alert; returns the channels it reached.

    Args:
        title: Short headline.
        body: Detail line.
        urgent: Breaks through quiet hours and do-not-disturb.
        speak: Also say it aloud in HAL's voice (never during quiet time unless urgent).
        channels: Restrict to some of desktop, phone, voice, telegram; default all configured.
        url: Link opened when the phone notification is tapped.
    """
    wanted = set(channels or settings().get("channels", ["desktop", "phone"]))
    hush = quiet() and not urgent
    reached = []
    if "desktop" in wanted and _desktop(title, body, urgent):
        reached.append("desktop")
    if "phone" in wanted and _ntfy(title, body, urgent, hush, url):
        reached.append("phone")
    if (speak or "voice" in wanted) and not hush and _speak(title, body):
        reached.append("voice")
    if "telegram" in wanted and _telegram(title, body):
        reached.append("telegram")
    con = _db()
    con.execute(
        "INSERT INTO sent VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), title, body, int(urgent), ",".join(reached)),
    )
    con.commit()
    return {"reached": reached, "quiet": hush}


def dnd(minutes: int = 60) -> str:
    """Turns do-not-disturb on for some minutes; 0 turns it off."""
    f = data_dir() / "dnd"
    if int(minutes) <= 0:
        f.unlink(missing_ok=True)
        return "do-not-disturb off"
    until = datetime.now() + timedelta(minutes=int(minutes))
    f.write_text(until.isoformat(timespec="seconds"))
    return f"do-not-disturb until {until:%H:%M}"


def state() -> dict:
    until = _dnd_until()
    return {
        "quiet": quiet(),
        "dnd_until": until.isoformat(timespec="minutes") if until else None,
        "quiet_hours": f"{settings().get('quiet_from', 22)}:00 to {settings().get('quiet_until', 8)}:00",
    }


def history(limit: int = 20) -> list[dict]:
    rows = _db().execute("SELECT * FROM sent ORDER BY at DESC LIMIT ?", (int(limit),)).fetchall()
    return [
        {"at": r[0], "title": r[1], "body": r[2], "urgent": bool(r[3]), "channels": r[4]}
        for r in rows
    ]
