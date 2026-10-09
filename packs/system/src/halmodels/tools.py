"""hal-models' tools: the local models in Ollama and what the GPU is doing.

Talks to Ollama's HTTP API and nvidia-smi. Pulling and deleting models, and
unloading one another program is using, change shared state, so deleting needs
confirmation through hal-hub.
"""
from __future__ import annotations

import json
import subprocess
import urllib.request

from .config import shared


def _api(path: str, payload: dict | None = None, timeout: float = 30, method: str | None = None):
    url = shared()["ollama_url"].rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return json.loads(body) if body.strip().startswith(b"{") else body.decode()


def installed(query: str = "") -> list[dict]:
    """Models installed in Ollama, with size and family."""
    out = []
    for m in _api("/api/tags")["models"]:
        if query and query.lower() not in m["name"].lower():
            continue
        d = m.get("details", {})
        out.append({"name": m["name"], "size_gb": round(m["size"] / 1e9, 1), "family": d.get("family"),
                    "parameters": d.get("parameter_size"), "quantisation": d.get("quantization_level")})
    return sorted(out, key=lambda x: x["name"])


def loaded() -> list[dict]:
    """Models loaded in memory now, with VRAM use and when they unload."""
    return [{"name": m["name"], "vram_gb": round(m.get("size_vram", 0) / 1e9, 1), "unloads_at": m.get("expires_at", "")[:19]}
            for m in _api("/api/ps")["models"]]


def gpu() -> dict:
    """GPU memory and use, and every program on it."""
    q = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.strip()
    if not q:
        return {"gpu": "no NVIDIA GPU found"}
    name, used, total, util, temp = [x.strip() for x in q.splitlines()[0].split(",")]
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
                          capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
    procs = []
    for a in apps:
        pid, path, mib = [x.strip() for x in a.split(",")]
        try:
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")[:120]
        except OSError:
            cmd = path
        procs.append({"pid": int(pid), "program": path.rsplit("/", 1)[-1], "memory_mb": int(mib), "command": cmd})
    return {"name": name, "memory_used_mb": int(used), "memory_total_mb": int(total), "use_percent": int(util),
            "temperature_c": int(temp), "programs": procs}


def load(model: str, minutes: int = 30) -> dict:
    """Loads a model into memory and keeps it there for some minutes."""
    _api("/api/generate", {"model": model, "keep_alive": f"{int(minutes)}m"}, timeout=600)
    return {"loaded": model, "for_minutes": int(minutes)}


def unload(model: str = "") -> dict:
    """Unloads one model, or every loaded model, to free VRAM."""
    names = [model] if model else [m["name"] for m in loaded()]
    for n in names:
        _api("/api/generate", {"model": n, "keep_alive": 0}, timeout=60)
    return {"unloaded": names}


def pull(model: str) -> dict:
    """Downloads a model from the Ollama library (can take a while)."""
    _api("/api/pull", {"model": model, "stream": False}, timeout=7200)
    return {"pulled": model}


def delete(model: str) -> dict:
    _api("/api/delete", {"model": model}, method="DELETE")
    return {"deleted": model}


def ask(model: str, prompt: str) -> dict:
    """Asks a specific local model a question directly."""
    out = _api("/api/chat", {"model": model, "stream": False, "think": False,
                             "messages": [{"role": "user", "content": prompt}]}, timeout=600)
    return {"model": model, "answer": out["message"]["content"].strip()}
