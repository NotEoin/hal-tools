"""hal-desktop's tools: launch apps, open things, and control the GNOME desktop.

Uses what a stock GNOME desktop provides: .desktop files and gtk-launch for
apps, gio for files and URLs, gsettings for theme, night light, wallpaper and
banners, wpctl (PipeWire) for sound, loginctl for the session, and the
xdg-desktop-portal Screenshot interface through PyGObject. The clipboard uses
wl-clipboard or xclip when installed.
"""
from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .config import data_dir

APP_DIRS = [Path("/usr/share/applications"), Path("~/.local/share/applications").expanduser(),
            Path("/var/lib/snapd/desktop/applications"), Path("/var/lib/flatpak/exports/share/applications"),
            Path("~/.local/share/flatpak/exports/share/applications").expanduser()]


def _run(*cmd: str, timeout: float = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _gset(schema: str, key: str, value: str | None = None) -> str:
    if value is None:
        return _run("gsettings", "get", schema, key).stdout.strip().strip("'")
    done = _run("gsettings", "set", schema, key, value)
    if done.returncode:
        raise RuntimeError(done.stderr.strip())
    return value


# -- apps -----------------------------------------------------------------------

def _apps() -> list[dict]:
    out, seen = [], set()
    for d in APP_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.desktop")):
            if f.name in seen:
                continue
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                cp.read(f, encoding="utf-8")
                e = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if e.get("NoDisplay", "false") == "true" or e.get("Type", "Application") != "Application":
                continue
            seen.add(f.name)
            out.append({"id": f.stem, "name": e.get("Name", f.stem), "generic": e.get("GenericName", ""),
                        "keywords": e.get("Keywords", ""), "categories": e.get("Categories", "")})
    return out


def apps(query: str = "") -> list[dict]:
    """Installed applications, optionally matching a word."""
    q = query.lower()
    found = [a for a in _apps() if not q or q in f"{a['name']} {a['generic']} {a['keywords']} {a['id']}".lower()]
    return [{"name": a["name"], "id": a["id"], "kind": a["generic"]} for a in found][:40]


def launch(app: str) -> dict:
    """Starts an application by name ('firefox', 'files', 'terminal', 'spotify')."""
    q = app.lower().strip()
    candidates = _apps()

    def score(a: dict) -> int:
        name, ident = a["name"].lower(), a["id"].lower()
        if q in (name, ident) or ident.endswith("." + q):
            return 3
        if name.startswith(q) or q in ident.split("."):
            return 2
        if q in f"{name} {a['generic'].lower()} {a['keywords'].lower()}":
            return 1
        return 0

    best = max(candidates, key=score, default=None)
    if not best or score(best) == 0:
        raise ValueError(f"no installed app matches {app!r}")
    subprocess.Popen(["gtk-launch", best["id"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return {"launched": best["name"]}


def open_item(target: str) -> dict:
    """Opens a URL, file or folder with its default application."""
    if not re.match(r"^[a-z][a-z0-9+.-]*://", target):
        p = Path(target).expanduser()
        if not p.exists():
            raise ValueError(f"{target} does not exist")
        target = str(p)
    subprocess.Popen(["gio", "open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return {"opened": target}


# -- sound ----------------------------------------------------------------------

def volume(level: int | None = None, change: int = 0, mute: str = "") -> dict:
    """Reads or sets the output volume (0 to 100), nudges it up or down, or mutes it (on, off, toggle)."""
    sink = "@DEFAULT_AUDIO_SINK@"
    if mute:
        _run("wpctl", "set-mute", sink, {"on": "1", "off": "0"}.get(mute, "toggle"))
    if level is not None:
        _run("wpctl", "set-volume", sink, f"{max(0, min(150, int(level))) / 100:.2f}")
    elif change:
        _run("wpctl", "set-volume", "-l", "1.5", sink, f"{abs(int(change))}%{'+' if int(change) > 0 else '-'}")
    out = _run("wpctl", "get-volume", sink).stdout.strip()
    m = re.search(r"([\d.]+)", out)
    return {"volume": round(float(m.group(1)) * 100) if m else None, "muted": "MUTED" in out}


def audio_devices() -> dict:
    """Speakers and microphones, with the defaults marked."""
    text = _run("wpctl", "status").stdout
    out: dict = {"outputs": [], "inputs": []}
    section = None
    for line in text.splitlines():
        if "Sinks:" in line:
            section = "outputs"
        elif "Sources:" in line:
            section = "inputs"
        elif re.search(r"(Filters|Streams|Devices|Clients):", line) or line.strip() in ("Video", "Settings"):
            section = None
        elif section:
            m = re.search(r"(\*)?\s+(\d+)\.\s+(.+?)\s*(\[vol:.*\])?$", line)
            if m:
                out[section].append({"id": int(m.group(2)), "name": m.group(3).strip(), "default": bool(m.group(1))})
    return out


def set_audio_output(device: str) -> dict:
    """Makes a speaker or headset the default output, by id or part of its name."""
    outputs = audio_devices()["outputs"]
    pick = next((d for d in outputs if str(d["id"]) == str(device) or device.lower() in d["name"].lower()), None)
    if not pick:
        raise ValueError(f"no output matches {device!r}; have {[d['name'] for d in outputs]}")
    _run("wpctl", "set-default", str(pick["id"]))
    return {"output": pick["name"]}


# -- look and feel ----------------------------------------------------------------

def theme(mode: str = "") -> dict:
    """Reads or sets light or dark mode."""
    schema = "org.gnome.desktop.interface"
    if mode:
        _gset(schema, "color-scheme", "prefer-dark" if mode.lower().startswith("d") else "default")
    return {"mode": "dark" if _gset(schema, "color-scheme") == "prefer-dark" else "light"}


def night_light(on: str = "") -> dict:
    """Reads or switches GNOME's night light (on, off)."""
    schema = "org.gnome.settings-daemon.plugins.color"
    if on:
        _gset(schema, "night-light-enabled", "true" if on.lower() in ("on", "true", "yes") else "false")
    return {"night_light": _gset(schema, "night-light-enabled") == "true"}


def wallpaper(path: str = "") -> dict:
    """Reads or sets the desktop wallpaper from an image file."""
    schema = "org.gnome.desktop.background"
    if path:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise ValueError(f"{path} is not a file")
        for key in ("picture-uri", "picture-uri-dark"):
            _gset(schema, key, p.as_uri())
    return {"wallpaper": _gset(schema, "picture-uri-dark") or _gset(schema, "picture-uri")}


def banners(on: str = "") -> dict:
    """Shows or hides notification banners (GNOME's do-not-disturb)."""
    schema = "org.gnome.desktop.notifications"
    if on:
        _gset(schema, "show-banners", "true" if on.lower() in ("on", "true", "yes") else "false")
    return {"banners": _gset(schema, "show-banners") == "true"}


# -- clipboard and screen --------------------------------------------------------------

def clipboard(text: str | None = None) -> dict:
    """Reads the clipboard, or copies text to it (needs wl-clipboard or xclip)."""
    if text is not None:
        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, timeout=5)
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, timeout=5)
        else:
            raise RuntimeError("install wl-clipboard (sudo apt install wl-clipboard) to use the clipboard")
        return {"copied": len(text)}
    if shutil.which("wl-paste"):
        return {"text": _run("wl-paste", "--no-newline").stdout[:8000]}
    if shutil.which("xclip"):
        return {"text": _run("xclip", "-selection", "clipboard", "-o").stdout[:8000]}
    raise RuntimeError("install wl-clipboard (sudo apt install wl-clipboard) to read the clipboard")


def _portal_shot(interactive: bool) -> str | None:
    """Asks the desktop portal for a screenshot; returns its file path, or None if refused.

    GNOME refuses silent screenshots to unsandboxed programs, so callers retry
    with interactive=True, which shows GNOME's own Share dialog.
    """
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    token = f"hal{int(time.time() * 1000)}"
    sender = bus.get_unique_name()[1:].replace(".", "_")
    handle = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
    loop, result = GLib.MainLoop(), {}

    def on_response(_c, _s, _p, _i, _sig, params):
        code, res = params.unpack()
        result.update(code=code, uri=res.get("uri"))
        loop.quit()

    sub = bus.signal_subscribe("org.freedesktop.portal.Desktop", "org.freedesktop.portal.Request", "Response",
                               handle, None, Gio.DBusSignalFlags.NO_MATCH_RULE, on_response)
    bus.call_sync("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                  "org.freedesktop.portal.Screenshot", "Screenshot",
                  GLib.Variant("(sa{sv})", ("", {"handle_token": GLib.Variant("s", token),
                                                 "interactive": GLib.Variant("b", interactive)})),
                  None, Gio.DBusCallFlags.NONE, 10000, None)
    GLib.timeout_add_seconds(60 if interactive else 15, loop.quit)
    loop.run()
    bus.signal_unsubscribe(sub)
    if result.get("code") != 0 or not result.get("uri"):
        return None
    return Gio.File.new_for_uri(result["uri"]).get_path()


def _shoot() -> str:
    """Returns a fresh screenshot's path, asking GNOME's permission dialog if a silent one is refused."""
    path = _portal_shot(False) or _portal_shot(True)
    if not path:
        raise RuntimeError("the screenshot was refused; press Share when GNOME asks")
    return path


def screenshot(path: str = "") -> dict:
    """Takes a screenshot of the whole screen through the desktop portal and saves it."""
    dest = Path(path).expanduser() if path else data_dir() / f"screen-{datetime.now():%Y%m%d-%H%M%S}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(_shoot(), dest)
    return {"saved": str(dest)}


# -- session ----------------------------------------------------------------------

def lock() -> dict:
    _run("loginctl", "lock-session")
    return {"locked": True}


def idle_seconds() -> dict:
    """How long the desktop has gone without keyboard or mouse input."""
    out = _run("gdbus", "call", "--session", "--dest", "org.gnome.Mutter.IdleMonitor", "--object-path",
               "/org/gnome/Mutter/IdleMonitor/Core", "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime").stdout
    m = re.search(r"(\d+)", out)
    return {"idle_seconds": int(m.group(1)) // 1000 if m else None}


def session() -> dict:
    """Desktop, display server, screen locked or not, and who is logged in."""
    sid = os.environ.get("XDG_SESSION_ID") or ""
    info = _run("loginctl", "show-session", sid, "-p", "LockedHint", "-p", "Type", "-p", "Desktop").stdout if sid else ""
    props = dict(l.split("=", 1) for l in info.splitlines() if "=" in l)
    return {"desktop": os.environ.get("XDG_CURRENT_DESKTOP"), "display": os.environ.get("XDG_SESSION_TYPE"),
            "locked": props.get("LockedHint") == "yes", "user": os.environ.get("USER"), **idle_seconds()}
