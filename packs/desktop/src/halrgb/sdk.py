"""A small client for the OpenRGB SDK network protocol (OpenRGB's --server, port 6742).

Speaks protocol version 3: device list and data, direct colour updates, mode
(effect) changes and saved profiles. Every packet starts with the header
'ORGB', a device index, a packet id and the payload size, all little-endian.
Stdlib only.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass, field

PROTOCOL = 3
REQUEST_CONTROLLER_COUNT = 0
REQUEST_CONTROLLER_DATA = 1
REQUEST_PROTOCOL_VERSION = 40
SET_CLIENT_NAME = 50
REQUEST_PROFILE_LIST = 150
REQUEST_LOAD_PROFILE = 152
UPDATE_LEDS = 1050
SET_CUSTOM_MODE = 1100
UPDATE_MODE = 1101


@dataclass
class Mode:
    """One lighting mode of a device."""

    index: int
    name: str
    raw: bytes  # the mode's bytes as received, re-sent to select it


@dataclass
class Device:
    """One RGB device and the modes it offers."""

    index: int
    name: str
    kind: int
    leds: int
    active_mode: int
    modes: list[Mode] = field(default_factory=list)
    zones: list[str] = field(default_factory=list)


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.d, self.i = data, 0

    def take(self, fmt: str):
        size = struct.calcsize(fmt)
        out = struct.unpack_from("<" + fmt, self.d, self.i)
        self.i += size
        return out if len(out) > 1 else out[0]

    def string(self) -> str:
        n = self.take("H")
        s = self.d[self.i : self.i + n].rstrip(b"\0").decode(errors="replace")
        self.i += n
        return s

    def skip(self, n: int) -> None:
        self.i += n


class Client:
    """A client for the OpenRGB SDK server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6742, name: str = "Hal") -> None:
        try:
            self.sock = socket.create_connection((host, port), timeout=5)
        except OSError as e:
            raise ConnectionError(
                f"OpenRGB's SDK server is not running on {host}:{port} "
                "(start it with: openrgb --server)"
            ) from e
        self.version = min(PROTOCOL, self._request_version())
        self._send(0, SET_CLIENT_NAME, name.encode() + b"\0")

    def close(self) -> None:
        """Closes the connection."""
        self.sock.close()

    def _send(self, device: int, packet: int, data: bytes = b"") -> None:
        self.sock.sendall(b"ORGB" + struct.pack("<III", device, packet, len(data)) + data)

    def _recv(self, packet: int) -> bytes:
        while True:
            head = self._exact(16)
            if head[:4] != b"ORGB":
                raise ConnectionError("not an OpenRGB server")
            _, pid, size = struct.unpack("<III", head[4:])
            body = self._exact(size)
            if pid == packet:
                return body

    def _exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("OpenRGB closed the connection")
            buf += chunk
        return buf

    def _request_version(self) -> int:
        self._send(0, REQUEST_PROTOCOL_VERSION, struct.pack("<I", PROTOCOL))
        self.sock.settimeout(2)
        try:
            return struct.unpack("<I", self._recv(REQUEST_PROTOCOL_VERSION))[0]
        except (TimeoutError, struct.error):
            return 0
        finally:
            self.sock.settimeout(5)

    def count(self) -> int:
        """Returns how many devices the server has."""
        self._send(0, REQUEST_CONTROLLER_COUNT)
        return struct.unpack("<I", self._recv(REQUEST_CONTROLLER_COUNT))[0]

    def device(self, index: int) -> Device:
        """Returns the device at `index`."""
        self._send(index, REQUEST_CONTROLLER_DATA, struct.pack("<I", self.version))
        r = _Reader(self._recv(REQUEST_CONTROLLER_DATA))
        r.take("I")
        kind = r.take("i")
        name = r.string()
        if self.version >= 1:
            r.string()  # vendor
        r.string()
        r.string()
        r.string()
        r.string()  # description, version, serial, location
        n_modes = r.take("H")
        active = r.take("i")
        modes = []
        for m in range(n_modes):
            start = r.i
            mode_name = r.string()
            # value, flags, speed min and max, [brightness min and max], colours min and max,
            # speed, [brightness], direction, colour mode: brightness arrived in protocol 3.
            r.skip(4 * (9 if self.version < 3 else 12))
            n_colours = r.take("H")
            r.skip(4 * n_colours)
            modes.append(Mode(m, mode_name, r.d[start : r.i]))
        zones = []
        for _ in range(r.take("H")):
            zones.append(r.string())
            r.skip(4 * 4)  # type, leds min, max, count
            matrix = r.take("H")
            r.skip(matrix)
        leds = r.take("H")
        return Device(index, name, kind, leds, active, modes, zones)

    def devices(self) -> list[Device]:
        """Returns every device."""
        return [self.device(i) for i in range(self.count())]

    def set_colour(self, dev: Device, rgb: tuple[int, int, int]) -> None:
        """Switches the device to its direct mode and sets every LED to one colour."""
        self._send(dev.index, SET_CUSTOM_MODE)
        colours = struct.pack("<BBBx", *rgb) * dev.leds
        payload = struct.pack("<H", dev.leds) + colours
        self._send(dev.index, UPDATE_LEDS, struct.pack("<I", 4 + len(payload)) + payload)

    def set_mode(self, dev: Device, mode: Mode) -> None:
        """Switches a device to a mode."""
        payload = struct.pack("<i", mode.index) + mode.raw
        self._send(dev.index, UPDATE_MODE, struct.pack("<I", 4 + len(payload)) + payload)

    def profiles(self) -> list[str]:
        """Returns the names of the saved profiles."""
        self._send(0, REQUEST_PROFILE_LIST)
        r = _Reader(self._recv(REQUEST_PROFILE_LIST))
        r.take("I")
        return [r.string() for _ in range(r.take("H"))]

    def load_profile(self, name: str) -> None:
        """Loads a saved profile by name."""
        self._send(0, REQUEST_LOAD_PROFILE, name.encode() + b"\0")
