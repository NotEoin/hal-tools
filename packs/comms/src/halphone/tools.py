"""hal-phone's tools: the phone, through KDE Connect.

Needs KDE Connect on the computer (kdeconnect-cli; GSConnect works the same on
GNOME) and the KDE Connect app on the phone, paired once. Sending an SMS needs
confirmation through hal-hub.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .config import settings

SETUP = ("KDE Connect is not installed: run 'sudo apt install kdeconnect', install the KDE Connect app "
         "on the phone, and pair them once")


def _cli(*args: str, timeout: float = 20) -> str:
    if not shutil.which("kdeconnect-cli"):
        raise RuntimeError(SETUP)
    done = subprocess.run(["kdeconnect-cli", *args], capture_output=True, text=True, timeout=timeout)
    if done.returncode:
        raise RuntimeError(done.stderr.strip() or "KDE Connect did not respond")
    return done.stdout.strip()


def devices() -> list[dict]:
    """Paired phones and tablets, and whether each is reachable now."""
    out = []
    for line in _cli("--list-devices").splitlines():
        m = re.match(r"- (.+?): (\S+) \((.+)\)", line)
        if m:
            out.append({"name": m.group(1), "id": m.group(2), "reachable": "reachable" in m.group(3)})
    return out


def _device(name: str = "") -> str:
    want = name or settings().get("phone", "")
    phones = [d for d in devices() if d["reachable"]]
    if not phones:
        raise RuntimeError("no paired phone is reachable; check it is on the same network with KDE Connect open")
    pick = next((d for d in phones if want and want.lower() in d["name"].lower()), phones[0])
    return pick["id"]


def ring(phone: str = "") -> dict:
    """Makes the phone ring loudly so you can find it."""
    _cli("-d", _device(phone), "--ring")
    return {"ringing": True}


def battery(phone: str = "") -> dict:
    """The phone's battery level."""
    dev = _device(phone)
    out = subprocess.run(["qdbus", "org.kde.kdeconnect", f"/modules/kdeconnect/devices/{dev}/battery", "charge"],
                         capture_output=True, text=True, timeout=10).stdout.strip() if shutil.which("qdbus") else ""
    return {"percent": int(out) if out.isdigit() else None}


def send_file(path: str, phone: str = "") -> dict:
    """Sends a file to the phone."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"{path} is not a file")
    _cli("-d", _device(phone), "--share", str(p), timeout=120)
    return {"sent": p.name}


def send_link(url: str, phone: str = "") -> dict:
    """Opens a link on the phone."""
    _cli("-d", _device(phone), "--share", url)
    return {"opened_on_phone": url}


def send_text(text: str, phone: str = "") -> dict:
    """Puts text on the phone's clipboard."""
    _cli("-d", _device(phone), "--share-text", text)
    return {"sent_text": len(text)}


def sms(number: str, message: str, phone: str = "") -> dict:
    """Sends a text message from the phone."""
    if not re.fullmatch(r"\+?[\d\s()-]{6,20}", number):
        raise ValueError(f"not a phone number: {number!r}")
    _cli("-d", _device(phone), "--send-sms", message, "--destination", number.replace(" ", ""))
    return {"sms_sent_to": number}


def notifications(phone: str = "") -> list[str]:
    """The notifications showing on the phone."""
    return _cli("-d", _device(phone), "--list-notifications").splitlines()[:30]
