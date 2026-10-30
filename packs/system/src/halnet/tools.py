"""hal-network's tools: how the computer is connected and how well.

Uses NetworkManager (nmcli), iproute2 and resolvectl, which ship with Ubuntu,
plus plain sockets and HTTPS for ping-free checks, the public IP and a speed
test against Cloudflare's speed endpoints. Scanning other machines' ports is
limited to the local network.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
import urllib.request

from hal_system import proc

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Hal/1.0"}


def _open(url: str, data: bytes | None = None, timeout: float = 30):
    req = urllib.request.Request(  # noqa: S310 - callers pass fixed https URLs
        url, data=data, headers=UA, method="POST" if data else "GET"
    )
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 - same fixed URLs


def _run(*cmd: str, timeout: float = 20) -> str:
    try:
        return proc.completed(cmd, timeout=timeout).stdout
    except (OSError, proc.ProcTimeout):
        return ""


def status() -> dict:
    """Connections, local addresses, gateway, DNS servers and any VPN."""
    devices = []
    for line in _run("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device").splitlines():
        dev, kind, state, conn = [*line.split(":"), "", "", "", ""][:4]
        if kind in ("loopback", "bridge") or dev.startswith(("veth", "docker", "br-")):
            continue
        addr = re.search(r"inet (\S+)", _run("ip", "-4", "addr", "show", dev))
        devices.append(
            {
                "device": dev,
                "type": kind,
                "state": state,
                "connection": conn,
                "address": addr.group(1) if addr else None,
            }
        )
    gw = re.search(r"default via (\S+) dev (\S+)", _run("ip", "route"))
    dns = re.findall(r"Current DNS Server: (\S+)|DNS Servers: (.+)", _run("resolvectl", "status"))
    vpns = [
        ln.split(":")[0]
        for ln in _run(
            "nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"
        ).splitlines()
        if re.search(r":(vpn|wireguard)$", ln)
    ]
    return {
        "devices": devices,
        "gateway": gw.group(1) if gw else None,
        "dns": sorted({x for pair in dns for x in " ".join(pair).split() if x}),
        "vpn": vpns,
        "online": _online(),
    }


def _online() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return True
    except OSError:
        return False


def wifi() -> dict:
    """The Wi-Fi network in use with its signal, and the networks in range."""
    rows = _run(
        "nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list"
    ).splitlines()
    nets = []
    for r in rows:
        parts = r.split(":")
        if len(parts) >= 5 and parts[1]:
            nets.append(
                {
                    "ssid": parts[1],
                    "signal": int(parts[2] or 0),
                    "security": parts[3],
                    "channel": parts[4],
                    "in_use": parts[0] == "*",
                }
            )
    if not nets:
        return {"wifi": "no Wi-Fi adapter or no networks in range"}
    return {
        "connected": next((n for n in nets if n["in_use"]), None),
        "in_range": sorted(nets, key=lambda n: -n["signal"])[:12],
    }


def public_ip() -> dict:
    with _open("https://ipinfo.io/json", timeout=10) as r:
        geo = json.loads(r.read())
    return {
        "ip": geo.get("ip"),
        "isp": geo.get("org"),
        "city": geo.get("city"),
        "country": geo.get("country"),
    }


def devices() -> list[dict]:
    """Other devices seen on the local network recently (neighbour table), named where known."""
    out = []
    for line in _run("ip", "neigh").splitlines():
        m = re.match(r"(\S+) dev (\S+)(?: lladdr (\S+))? (\S+)", line)
        if not m or m.group(4) in ("FAILED", "INCOMPLETE") or ":" in m.group(1):
            continue
        ip = m.group(1)
        try:
            name = socket.gethostbyaddr(ip)[0]
        except OSError:
            name = None
        out.append({"ip": ip, "mac": m.group(3), "name": name, "state": m.group(4).lower()})
    return out


def ping(host: str = "1.1.1.1", count: int = 4) -> dict:
    """Round-trip time and packet loss to a host."""
    out = _run("ping", "-c", str(max(1, min(20, int(count)))), "-W", "2", host, timeout=60)
    loss = re.search(r"(\d+(?:\.\d+)?)% packet loss", out)
    rtt = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)", out)
    if not loss:
        raise ValueError(f"cannot reach {host}")
    return {
        "host": host,
        "loss_percent": float(loss.group(1)),
        "avg_ms": float(rtt.group(2)) if rtt else None,
        "max_ms": float(rtt.group(3)) if rtt else None,
    }


def port(host: str, port: int) -> dict:
    """Whether a TCP port is open on a host (only this machine or the local network)."""
    addr = socket.gethostbyname(host)
    ip = ipaddress.ip_address(addr)
    if not (ip.is_private or ip.is_loopback):
        raise ValueError("port checks are limited to this machine and the local network")
    try:
        socket.create_connection((addr, int(port)), timeout=3).close()
        return {"host": host, "port": int(port), "open": True}
    except OSError:
        return {"host": host, "port": int(port), "open": False}


def listening() -> list[dict]:
    """Programs on this machine listening for network connections."""
    out = []
    for line in _run("ss", "-ltnpH").splitlines():
        p = line.split()
        if len(p) >= 4:
            prog = re.search(r'"([^"]+)"', line)
            out.append({"address": p[3], "program": prog.group(1) if prog else None})
    return out


def speed_test(megabytes: int = 25) -> dict:
    """Download and upload speed in megabits per second, and latency, against Cloudflare."""
    size = max(1, min(100, int(megabytes))) * 1_000_000
    t = time.time()
    _open("https://speed.cloudflare.com/__down?bytes=0", timeout=10).read()
    latency = (time.time() - t) * 1000
    t = time.time()
    with _open(f"https://speed.cloudflare.com/__down?bytes={size}", timeout=120) as r:
        got = len(r.read())
    down = got * 8 / (time.time() - t) / 1e6
    # urllib sends a body as form data, which throttles the upload; a raw socket measures the line.
    import http.client

    up_size = max(size // 2, 5_000_000)
    t = time.time()
    conn = http.client.HTTPSConnection("speed.cloudflare.com", timeout=120)
    conn.request(
        "POST",
        "/__up",
        body=b"0" * up_size,
        headers={**UA, "Content-Type": "application/octet-stream"},
    )
    conn.getresponse().read()
    up = up_size * 8 / (time.time() - t) / 1e6
    return {
        "download_mbps": round(down, 1),
        "upload_mbps": round(up, 1),
        "latency_ms": round(latency),
    }
