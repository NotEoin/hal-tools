"""hal-rgb's tools: colours, effects, brightness and profiles through OpenRGB, and lights that
follow Hal.

Talks to OpenRGB's SDK server (start it with `openrgb --server`, or the unit in
systemd/). Colours are names ('warm white', 'hal red'), #rrggbb or 'r,g,b'.
"""

from __future__ import annotations

import re

from .sdk import Client, Device
from .settings import settings

COLOURS = {
    "red": (255, 0, 0),
    "hal red": (220, 20, 10),
    "dark red": (120, 0, 0),
    "orange": (255, 100, 0),
    "amber": (255, 150, 0),
    "yellow": (255, 210, 0),
    "lime": (150, 255, 0),
    "green": (0, 255, 0),
    "teal": (0, 160, 140),
    "cyan": (0, 255, 255),
    "sky blue": (80, 180, 255),
    "blue": (0, 0, 255),
    "navy": (0, 0, 120),
    "indigo": (75, 0, 200),
    "purple": (140, 0, 255),
    "violet": (180, 80, 255),
    "magenta": (255, 0, 255),
    "pink": (255, 80, 160),
    "white": (255, 255, 255),
    "warm white": (255, 170, 90),
    "cool white": (200, 220, 255),
    "off": (0, 0, 0),
    "black": (0, 0, 0),
}


def parse_colour(colour: str) -> tuple[int, int, int]:
    """Returns (r, g, b) for a colour name, #rrggbb, or 'r,g,b'."""
    c = colour.strip().lower()
    if c in COLOURS:
        return COLOURS[c]
    if c.removeprefix("light ") in COLOURS:
        return tuple(min(255, int(v + (255 - v) * 0.5)) for v in COLOURS[c.removeprefix("light ")])
    m = re.fullmatch(r"#?([0-9a-f]{6})", c)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    parts = re.findall(r"\d+", c)
    if len(parts) == 3:
        return tuple(max(0, min(255, int(p))) for p in parts)
    raise ValueError(
        f"unknown colour {colour!r}; try a name such as {', '.join(list(COLOURS)[:8])} or #ff8800"
    )


def _scale(rgb: tuple[int, int, int], brightness: int) -> tuple[int, int, int]:
    f = max(0, min(100, int(brightness))) / 100
    return tuple(int(v * f) for v in rgb)


def _client() -> Client:
    cfg = settings()
    return Client(cfg["host"], int(cfg["port"]))


def _targets(c: Client, device: str) -> list[Device]:
    devs = c.devices()
    if not device or device.lower() in ("all", "everything"):
        return devs
    picked = [d for d in devs if device.lower() in d.name.lower() or str(d.index) == device]
    if not picked:
        raise ValueError(
            f"no lighting device matches {device!r}; have {sorted({d.name for d in devs})}"
        )
    return picked


def devices() -> list[dict]:
    """Lighting devices with their LEDs, zones and effects."""
    c = _client()
    try:
        return [
            {
                "index": d.index,
                "name": d.name,
                "leds": d.leds,
                "zones": d.zones,
                "effects": [m.name for m in d.modes],
            }
            for d in c.devices()
        ]
    finally:
        c.close()


def colour(colour: str, device: str = "", brightness: int = 100) -> dict:
    """Sets lights to one colour: all of them, or those matching a device name."""
    rgb = _scale(parse_colour(colour), brightness)
    c = _client()
    try:
        done = []
        for d in _targets(c, device):
            c.set_colour(d, rgb)
            done.append(d.name)
        return {"colour": "#{:02x}{:02x}{:02x}".format(*rgb), "devices": sorted(set(done))}
    finally:
        c.close()


def off(device: str = "") -> dict:
    """Turns the lights off."""
    return colour("off", device)


def effect(effect: str, device: str = "") -> dict:
    """Switches to a built-in effect, such as rainbow or breathing, where devices have it."""
    want = effect.lower()
    c = _client()
    try:
        done, missing = [], []
        for d in _targets(c, device):
            mode = next((m for m in d.modes if m.name.lower() == want), None) or next(
                (
                    m
                    for m in d.modes
                    if want in m.name.lower() or m.name.lower().startswith(want[:5])
                ),
                None,
            )
            if mode:
                c.set_mode(d, mode)
                done.append(f"{d.name}: {mode.name}")
            else:
                missing.append(d.name)
        return {"set": done, "no_such_effect": sorted(set(missing))}
    finally:
        c.close()


def profiles() -> list[str]:
    """Returns the names of the saved lighting profiles."""
    c = _client()
    try:
        return c.profiles()
    finally:
        c.close()


def profile(name: str) -> dict:
    """Loads a profile saved in OpenRGB."""
    c = _client()
    try:
        names = c.profiles()
        match = next((p for p in names if p.lower() == name.lower()), None)
        if not match:
            raise ValueError(f"no profile {name!r}; saved: {names}")
        c.load_profile(match)
        return {"loaded": match}
    finally:
        c.close()


def state(state: str) -> dict:
    """Shows one of Hal's states (idle, listening, ...) in the configured colour."""
    states = settings()["states"]
    if state not in states:
        raise ValueError(f"state must be one of {', '.join(states)}")
    spec = states[state]
    return colour(spec["colour"], settings().get("follow_device", ""), spec.get("brightness", 100))
