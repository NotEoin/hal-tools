"""hal-lang's tools: language work by the local model.

Every tool takes text (or the clipboard's text, through the hub's
`desktop_clipboard`, when no text is given) and returns plain text. Nothing
leaves the machine.
"""

from __future__ import annotations

import json
import logging

from halhub import client
from halkit import llm as halkit_llm

MODEL_TIMEOUT_S = 300.0  # a local model on a cold start can take minutes to answer
MAX_TEXT_CHARS = 20000  # longer input exceeds the chat model context

log = logging.getLogger(__name__)
CALLER = "lang"  # the module name the hub checks against `calls`
HUB_TIMEOUT_S = 30.0  # reading the clipboard is instant; a stuck desktop must not hang a rewrite


def _text(text: str) -> str:
    """Returns `text`, or the clipboard's text when it is blank; raises when both are empty."""
    if text.strip():
        return text
    try:
        clip = client.call("desktop_clipboard", {}, CALLER, timeout=HUB_TIMEOUT_S)
    except (client.ToolDenied, client.ToolFailed) as exc:
        log.warning("clipboard not read: %s", exc)
        clip = None
    clip_text = clip.get("text", "") if isinstance(clip, dict) else ""
    if clip_text.strip():
        return clip_text
    raise ValueError("give the text, or copy it to the clipboard first")


def _ask(system: str, text: str) -> str:
    return halkit_llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": text[:MAX_TEXT_CHARS]}],
        timeout=MODEL_TIMEOUT_S,
    ).strip()


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
    raw = halkit_llm.chat(
        [
            {
                "role": "system",
                "content": f"Proofread the text: fix spelling ({spelling}), grammar and "
                "punctuation only; do not rephrase. Reply with JSON: "
                '{"corrected": the full corrected text, "changes": [short descriptions]}',
            },
            {"role": "user", "content": _text(text)},
        ],
        timeout=MODEL_TIMEOUT_S,
        temperature=0.1,
    )
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        out = {}
    if not isinstance(out, dict):
        out = {}
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
    """Summarises a text in at most `words` words."""
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
