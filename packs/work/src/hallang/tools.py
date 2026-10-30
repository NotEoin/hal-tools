"""hal-lang's tools: language work by the local model.

Every tool takes text (or the clipboard's text, through hal-hub's
desktop_clipboard, when no text is given) and returns plain text. Nothing
leaves the machine.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from . import llm


def _text(text: str) -> str:
    if text.strip():
        return text
    exe = shutil.which("hal-hub")
    if exe:
        out = subprocess.run(
            [exe, "desktop_clipboard"], capture_output=True, text=True, timeout=30
        ).stdout
        try:
            clip = json.loads(out).get("text", "")
        except (json.JSONDecodeError, AttributeError):
            clip = ""
        if clip.strip():
            return clip
    raise ValueError("give the text, or copy it to the clipboard first")


def _ask(system: str, text: str) -> str:
    busy = llm.gpu_busy()
    if busy:
        raise RuntimeError(f"the GPU is in use by {busy}")
    return llm.chat(system, text[:20000]).strip()


def translate(text: str = "", to: str = "English") -> dict:
    """Translates text into a language."""
    out = _ask(
        f"Translate the user's text into {to}. Keep the meaning, tone and formatting. "
        "Output only the translation.",
        _text(text),
    )
    return {"to": to, "translation": out}


def proofread(text: str = "", british: bool = True) -> dict:
    """Corrects spelling, grammar and punctuation, changing nothing else, and lists the changes."""
    spelling = "British" if british else "American"
    out = llm.chat_json(
        f"Proofread the text: fix spelling ({spelling}), grammar and punctuation only; "
        "do not rephrase. "
        'Reply with JSON: {"corrected": the full corrected text, "changes": [short descriptions]}',
        _text(text),
    )
    return {"corrected": out.get("corrected", ""), "changes": out.get("changes", [])}


def rewrite(text: str = "", tone: str = "professional", length: str = "same") -> dict:
    """Rewrites text in a tone (professional, friendly, formal, casual, concise) and length."""
    out = _ask(
        f"Rewrite the user's text in a {tone} tone, {length} length as the original "
        f"unless told otherwise ('shorter', 'longer'). Keep every fact. "
        "Output only the rewritten text.",
        _text(text),
    )
    return {"tone": tone, "text": out}


def summarise(text: str = "", words: int = 80) -> dict:
    out = _ask(
        f"Summarise the user's text in at most {int(words)} words of plain prose. "
        "Use only the text.",
        _text(text),
    )
    return {"summary": out}


def explain(text: str = "", audience: str = "someone new to the subject") -> dict:
    """Explains text (a letter, a contract clause, code, jargon) simply."""
    out = _ask(
        f"Explain the user's text clearly and briefly for {audience}. "
        "Say what it means and anything to watch for.",
        _text(text),
    )
    return {"explanation": out}


def reply(message: str = "", intent: str = "", tone: str = "friendly") -> dict:
    """Drafts a reply to a message, saying what the user wants to say."""
    out = _ask(
        f"Draft a {tone} reply to the message from the user's point of view. "
        "What they want to say: "
        f"{intent or 'a sensible, helpful reply'}. Output only the reply.",
        _text(message),
    )
    return {"reply": out}
