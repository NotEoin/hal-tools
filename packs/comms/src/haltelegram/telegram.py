"""A small client for the Telegram Bot API over urllib."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

LIMIT = 4000    # Telegram's limit is 4096 characters per message


class Telegram:
    def __init__(self, token: str) -> None:
        self.base = f"https://api.telegram.org/bot{token}"
        self.files = f"https://api.telegram.org/file/bot{token}"

    def call(self, method: str, timeout: float = 70, **params) -> dict:
        data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
        with urllib.request.urlopen(f"{self.base}/{method}", data=data, timeout=timeout) as r:
            reply = json.loads(r.read())
        if not reply.get("ok"):
            raise RuntimeError(f"{method}: {reply}")
        return reply["result"]

    def upload(self, method: str, field: str, path: Path, **params) -> dict:
        boundary = uuid.uuid4().hex
        body = b""
        for key, value in params.items():
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n"
                     f"{value}\r\n").encode()
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
                 f"filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(f"{self.base}/{method}", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())

    def download(self, file_id: str, dest: Path) -> Path:
        info = self.call("getFile", file_id=file_id)
        urllib.request.urlretrieve(f"{self.files}/{info['file_path']}", dest)
        return dest

    def send(self, chat: int, text: str) -> None:
        for start in range(0, len(text) or 1, LIMIT):
            self.call("sendMessage", chat_id=chat, text=text[start:start + LIMIT] or "(nothing)")

    def typing(self, chat: int) -> None:
        """Shows "typing..." in the chat; never raises."""
        try:
            self.call("sendChatAction", timeout=10, chat_id=chat, action="typing")
        except (OSError, RuntimeError):
            pass
