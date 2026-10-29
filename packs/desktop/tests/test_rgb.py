"""Tests for colour parsing and the SDK packets, against a fake OpenRGB server."""

import os
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _string(s: str) -> bytes:
    b = s.encode() + b"\0"
    return struct.pack("<H", len(b)) + b


def _device(name: str, leds: int, modes: list[str]) -> bytes:
    body = (
        struct.pack("<i", 0)
        + _string(name)
        + b"".join(_string(x) for x in ("vendor", "desc", "1", "sn", "loc"))
    )
    body += struct.pack("<Hi", len(modes), 0)
    for m in modes:
        body += _string(m) + struct.pack("<12I", *range(12)) + struct.pack("<H", 0)
    body += (
        struct.pack("<H", 1)
        + _string("zone")
        + struct.pack("<4I", 0, 0, leds, leds)
        + struct.pack("<H", 0)
    )
    body += struct.pack("<H", leds) + b"".join(
        _string(f"led{i}") + struct.pack("<I", i) for i in range(leds)
    )
    body += struct.pack("<H", leds) + b"\0\0\0\0" * leds
    return struct.pack("<I", len(body) + 4) + body


class FakeServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen()
        self.port = self.srv.getsockname()[1]
        self.received = []

    def reply(self, conn, pid, data):
        conn.sendall(b"ORGB" + struct.pack("<III", 0, pid, len(data)) + data)

    def run(self):
        while True:
            conn, _ = self.srv.accept()
            while True:
                head = conn.recv(16)
                if len(head) < 16:
                    break
                dev, pid, size = struct.unpack("<III", head[4:])
                data = b""
                while len(data) < size:
                    data += conn.recv(size - len(data))
                self.received.append((dev, pid, data))
                if pid == 40:
                    self.reply(conn, 40, struct.pack("<I", 3))
                elif pid == 0:
                    self.reply(conn, 0, struct.pack("<I", 1))
                elif pid == 1:
                    self.reply(conn, 1, _device("Test GPU", 3, ["Static", "Rainbow"]))


def _wait_for(server, pid, timeout=2.0):
    """Waits until the fake server has read a packet: the client may close before the read."""
    import time

    end = time.time() + timeout
    while time.time() < end and pid not in [p for _, p, _ in server.received]:
        time.sleep(0.01)


class RgbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = FakeServer()
        cls.server.start()
        cls.tmp = tempfile.TemporaryDirectory()
        cfg = Path(cls.tmp.name) / "c.toml"
        cfg.write_text(f"[rgb]\nport = {cls.server.port}\n")
        os.environ["HAL_CONFIG"] = str(cfg)
        from halrgb import tools

        cls.tools = tools

    def test_colour_names_and_codes(self):
        self.assertEqual(self.tools.parse_colour("#ff8800"), (255, 136, 0))
        with self.assertRaises(ValueError):
            self.tools.parse_colour("not a colour")

    def test_devices_are_parsed(self):
        self.assertEqual(self.tools.devices()[0]["effects"], ["Static", "Rainbow"])

    def test_colour_sends_custom_mode_then_every_led(self):
        self.server.received.clear()
        self.tools.colour("red", brightness=50)
        _wait_for(self.server, 1050)
        pids = [p for _, p, _ in self.server.received]
        self.assertLess(pids.index(1100), pids.index(1050))
        data = next(d for _, p, d in self.server.received if p == 1050)
        self.assertEqual(struct.unpack_from("<IH", data), (len(data), 3))
        self.assertEqual(data[6:10], bytes([127, 0, 0, 0]))

    def test_effect_selects_matching_mode(self):
        self.server.received.clear()
        out = self.tools.effect("rainbow")
        self.assertEqual(out["set"], ["Test GPU: Rainbow"])
        _wait_for(self.server, 1101)
        data = next(d for _, p, d in self.server.received if p == 1101)
        self.assertEqual(struct.unpack_from("<i", data, 4)[0], 1)


if __name__ == "__main__":
    unittest.main()
