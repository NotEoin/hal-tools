"""hal-screen's tools: Hal looks at the screen, or an image, with a local vision model.

Screenshots come from the xdg-desktop-portal (through PyGObject), so they work
under Wayland; the image goes to the configured Ollama vision model. Model work
waits while another program holds the GPU.
"""

from __future__ import annotations

import base64
import shutil
import time
from datetime import datetime
from pathlib import Path

from halkit import llm as halkit_llm

from .settings import data_dir, settings

MODEL_TIMEOUT_S = 300.0  # a local model on a cold start can take minutes to answer

DESCRIBE = (
    "You are looking at a screenshot of the user's computer screen. Answer briefly and concretely."
)
READ = (
    "Transcribe all readable text in this image exactly, top to bottom, keeping line breaks. "
    "Output only the text."
)
ERROR = (
    "This screenshot shows a problem on the user's computer. Find the error message, "
    "quote it, explain in "
    "plain words what it means, and give the most likely fix in two or three steps."
)


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

    sub = bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        handle,
        None,
        Gio.DBusSignalFlags.NO_MATCH_RULE,
        on_response,
    )
    bus.call_sync(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.Screenshot",
        "Screenshot",
        GLib.Variant(
            "(sa{sv})",
            (
                "",
                {
                    "handle_token": GLib.Variant("s", token),
                    "interactive": GLib.Variant("b", interactive),
                },
            ),
        ),
        None,
        Gio.DBusCallFlags.NONE,
        10000,
        None,
    )
    GLib.timeout_add_seconds(60 if interactive else 15, loop.quit)
    loop.run()
    bus.signal_unsubscribe(sub)
    if result.get("code") != 0 or not result.get("uri"):
        return None
    return Gio.File.new_for_uri(result["uri"]).get_path()


def _shoot() -> str:
    """Returns a fresh screenshot's path, asking GNOME's dialog if a silent one is refused."""
    path = _portal_shot(False) or _portal_shot(True)
    if not path:
        raise RuntimeError("the screenshot was refused; press Share when GNOME asks")
    return path


def capture() -> Path:
    """Takes a screenshot; returns the saved PNG, keeping only the newest few."""
    dest = data_dir() / f"screen-{datetime.now():%Y%m%d-%H%M%S}.png"
    shutil.move(_shoot(), dest)
    for old in sorted(data_dir().glob("screen-*.png"))[: -int(settings()["keep"])]:
        old.unlink()
    return dest


def _look(image: Path, system: str, question: str = "") -> str:
    b64 = base64.b64encode(image.read_bytes()).decode()
    question = question or "Describe what is on the screen."
    return halkit_llm.chat(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            },
        ],
        timeout=MODEL_TIMEOUT_S,
    ).strip()


def describe(question: str = "") -> dict:
    """Answers a question about what is on the screen now (or describes it)."""
    shot = capture()
    return {"answer": _look(shot, DESCRIBE, question), "screenshot": str(shot)}


def read_text() -> dict:
    """Reads the text on the screen."""
    shot = capture()
    return {"text": _look(shot, READ, "Transcribe the text."), "screenshot": str(shot)}


def explain_error() -> dict:
    """Finds the error message on screen and explains how to fix it."""
    shot = capture()
    return {
        "explanation": _look(shot, ERROR, "What is the error and how do I fix it?"),
        "screenshot": str(shot),
    }


def describe_image(path: str, question: str = "") -> dict:
    """Answers a question about an image file (or describes it)."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"{path} is not a file")
    return {
        "answer": _look(
            p, "Answer about this image briefly and concretely.", question or "Describe this image."
        )
    }
