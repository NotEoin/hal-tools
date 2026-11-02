"""A small client for the Telegram Bot API over urllib."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

NO_PREVIEW = json.dumps({"is_disabled": True})
LIMIT = 4000  # Telegram's limit is 4096 characters per message


class Telegram:
    """The Bot API calls the bridge needs."""

    def __init__(self, token: str) -> None:
        self.base = f"https://api.telegram.org/bot{token}"
        self.files = f"https://api.telegram.org/file/bot{token}"

    def call(self, method: str, timeout: float = 70, **params) -> dict:
        """Calls a Bot API method and returns its decoded reply."""
        data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
        with urllib.request.urlopen(f"{self.base}/{method}", data=data, timeout=timeout) as r:  # noqa: S310 - https URL on the fixed Telegram API host
            reply = json.loads(r.read())
        if not reply.get("ok"):
            raise RuntimeError(f"{method}: {reply}")
        return reply["result"]

    def upload(self, method: str, field: str, path: Path, **params) -> dict:
        """Sends a file to a Bot API method as a multipart upload."""
        boundary = uuid.uuid4().hex
        body = b""
        for key, value in params.items():
            body += (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
            ).encode()
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
            f'filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
        ).encode()
        body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(  # noqa: S310 - https URL on the fixed Telegram API host
            f"{self.base}/{method}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - https URL on the fixed Telegram API host
            return json.loads(r.read())

    def download(self, file_id: str, dest: Path) -> Path:
        """Downloads a file by its Telegram id to `dest` and returns `dest`."""
        info = self.call("getFile", file_id=file_id)
        urllib.request.urlretrieve(f"{self.files}/{info['file_path']}", dest)  # noqa: S310 - https URL on the fixed Telegram API host
        return dest

    def send(self, chat: int, text: str, buttons: list[tuple[str, str]] | None = None) -> None:
        """Sends text in chunks; link previews stay off (R-new-2); buttons go on the last chunk."""
        starts = list(range(0, len(text) or 1, LIMIT))
        for start in starts:
            markup = None
            if buttons and start == starts[-1]:
                keyboard = [[{"text": label, "callback_data": data} for label, data in buttons]]
                markup = json.dumps({"inline_keyboard": keyboard})
            self.call(
                "sendMessage",
                chat_id=chat,
                text=text[start : start + LIMIT] or "(nothing)",
                link_preview_options=NO_PREVIEW,
                reply_markup=markup,
            )

    def answer_callback(self, query_id: str, text: str = "") -> None:
        """Stops the button spinner; never raises."""
        try:
            self.call(
                "answerCallbackQuery", timeout=10, callback_query_id=query_id, text=text or None
            )
        except (OSError, RuntimeError):
            pass

    def typing(self, chat: int) -> None:
        """Shows "typing..." in the chat; never raises."""
        try:
            self.call("sendChatAction", timeout=10, chat_id=chat, action="typing")
        except (OSError, RuntimeError):
            pass
