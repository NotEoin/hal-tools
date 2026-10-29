"""hal-media's tools: control whatever is playing, and play local music.

Players are reached over MPRIS on the session bus (Spotify, browsers, VLC,
Rhythmbox and most others). Local music is found by file name and tags in the
configured folders and played with the configured player. Needs PyGObject.
"""
from __future__ import annotations

import re
import subprocess
import urllib.parse
from pathlib import Path

from .config import settings

MPRIS = "org.mpris.MediaPlayer2"
AUDIO = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".wma"}


def _bus():
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio
    return Gio.bus_get_sync(Gio.BusType.SESSION, None)


def _call(bus, dest: str, iface: str, method: str, args=None):
    from gi.repository import Gio
    return bus.call_sync(dest, "/org/mpris/MediaPlayer2", iface, method, args, None, Gio.DBusCallFlags.NONE, 3000, None)


def _players(bus) -> list[str]:
    names = bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", "ListNames",
                          None, None, 0, 3000, None).unpack()[0]
    return sorted(n for n in names if n.startswith(MPRIS + "."))


def _props(bus, dest: str) -> dict:
    from gi.repository import GLib
    v = _call(bus, dest, "org.freedesktop.DBus.Properties", "GetAll", GLib.Variant("(s)", (MPRIS + ".Player",)))
    return v.unpack()[0]


def _pick(bus, player: str = "") -> str:
    players = _players(bus)
    if not players:
        raise RuntimeError("nothing is playing and no media player is open")
    if player:
        match = [p for p in players if player.lower() in p.lower()]
        if not match:
            raise ValueError(f"no player matches {player!r}; open: {[p.split('.')[3] for p in players]}")
        return match[0]
    playing = [p for p in players if _props(bus, p).get("PlaybackStatus") == "Playing"]
    return (playing or players)[0]


def status() -> list[dict]:
    """Every media player with what it is playing."""
    bus = _bus()
    out = []
    for p in _players(bus):
        try:
            props = _props(bus, p)
        except Exception:  # noqa: BLE001 - a player that will not answer is left out
            continue
        meta = props.get("Metadata", {})
        out.append({"player": p.split(".", 3)[3], "status": props.get("PlaybackStatus"),
                    "title": meta.get("xesam:title"), "artist": ", ".join(meta.get("xesam:artist") or []),
                    "album": meta.get("xesam:album"),
                    "position_s": round(props.get("Position", 0) / 1e6) if props.get("Position") else None,
                    "length_s": round(meta.get("mpris:length", 0) / 1e6) if meta.get("mpris:length") else None})
    return out


def control(action: str, player: str = "") -> dict:
    """Play, pause, toggle, next, previous or stop."""
    methods = {"play": "Play", "pause": "Pause", "toggle": "PlayPause", "next": "Next",
               "previous": "Previous", "stop": "Stop"}
    if action not in methods:
        raise ValueError(f"action must be one of {', '.join(methods)}")
    bus = _bus()
    dest = _pick(bus, player)
    _call(bus, dest, MPRIS + ".Player", methods[action])
    return {"player": dest.split(".", 3)[3], "done": action}


def seek(seconds: int, player: str = "") -> dict:
    """Skips forward (positive) or back (negative) by some seconds."""
    from gi.repository import GLib
    bus = _bus()
    dest = _pick(bus, player)
    _call(bus, dest, MPRIS + ".Player", "Seek", GLib.Variant("(x)", (int(seconds) * 1_000_000,)))
    return {"seeked": int(seconds)}


def _library() -> list[Path]:
    files = []
    for d in settings()["music_dirs"]:
        root = Path(d).expanduser()
        if root.is_dir():
            files += [p for p in root.rglob("*") if p.suffix.lower() in AUDIO]
    return files


def play_music(query: str = "", shuffle: bool = False) -> dict:
    """Plays local music whose path (artist, album or title) matches the words, or everything."""
    words = [w for w in re.findall(r"\w+", query.lower()) if w not in ("by", "the", "some", "song", "music", "play")]
    hits = sorted(p for p in _library() if all(w in str(p).lower() for w in words))
    if not hits:
        raise ValueError(f"no music matches {query!r} in {settings()['music_dirs']}")
    player = settings()["player"]
    args = [player, *(["--random"] if shuffle and player == "vlc" else []), *map(str, hits[:200])]
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"playing": len(hits), "first": hits[0].stem}


def youtube(query: str) -> dict:
    """Opens a YouTube search in the browser."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    subprocess.Popen(["gio", "open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"opened": url}


def play_url(url: str) -> dict:
    """Plays a stream or file URL (radio, podcast) in the configured player."""
    subprocess.Popen([settings()["player"], url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return {"playing": url}
