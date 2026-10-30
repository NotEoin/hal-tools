"""hal-files' tools: find, read, summarise and tidy the owner's files.

Searches walk the configured roots, skipping caches, virtual environments,
version-control folders and the trash. Reading handles text, Markdown, code,
PDF (pdftotext), Word and OpenDocument files. Tidying Downloads moves files
into folders by type and needs confirmation through hal-hub.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path

from hal_work import proc

from . import llm
from .settings import settings

SKIP = {
    ".cache",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".local",
    ".npm",
    ".npm-global",
    ".cargo",
    ".rustup",
    "snap",
    ".mozilla",
    ".config",
    "site-packages",
    ".trash",
    ".Trash-1000",
    "miniconda3",
    "anaconda3",
    ".obsidian",
    ".ollama",
    ".gradle",
    ".m2",
}
KINDS = {
    "documents": {
        ".pdf",
        ".doc",
        ".docx",
        ".odt",
        ".txt",
        ".md",
        ".rtf",
        ".tex",
        ".pages",
        ".epub",
    },
    "spreadsheets": {".xls", ".xlsx", ".ods", ".csv"},
    "presentations": {".ppt", ".pptx", ".odp", ".key"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".heic", ".bmp", ".tiff"},
    "videos": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "audio": {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus"},
    "archives": {".zip", ".tar", ".gz", ".xz", ".7z", ".rar", ".bz2", ".zst"},
    "code": {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".rs",
        ".go",
        ".rb",
        ".sh",
        ".html",
        ".css",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ipynb",
        ".sql",
    },
    "installers": {".deb", ".AppImage", ".rpm", ".snap", ".flatpakref", ".run"},
}
SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(b|kb|mb|gb|tb)?", re.I)


def _roots(root: str = "") -> list[Path]:
    if root:
        p = Path(root).expanduser()
        if not p.is_dir():
            raise ValueError(f"{root} is not a folder")
        return [p]
    return [Path(r).expanduser() for r in settings()["roots"] if Path(r).expanduser().is_dir()]


def _walk(roots: list[Path], max_files: int = 300_000):
    seen = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in SKIP and not (d.startswith(".") and d not in (".config",))
            ]
            for f in filenames:
                seen += 1
                if seen > max_files:
                    return
                yield Path(dirpath) / f


def _bytes(text: str) -> int:
    m = SIZE.fullmatch(text.strip().replace(" ", ""))
    if not m:
        raise ValueError(f"cannot read the size {text!r}")
    return int(
        float(m.group(1))
        * {"b": 1, "kb": 1e3, "mb": 1e6, "gb": 1e9, "tb": 1e12}[(m.group(2) or "b").lower()]
    )


def _info(p: Path) -> dict:
    st = p.stat()
    return {
        "path": str(p),
        "size_mb": round(st.st_size / 1e6, 2),
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
    }


def find(
    name: str = "",
    kind: str = "",
    larger_than: str = "",
    modified_days: int = 0,
    root: str = "",
    limit: int = 25,
) -> list[dict]:
    """Files whose name has all the words, of a kind, above a size, changed in the last N days."""
    words = name.lower().split()
    exts = KINDS.get(kind.lower()) if kind else None
    if kind and exts is None:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    min_size = _bytes(larger_than) if larger_than else 0
    since = time.time() - int(modified_days) * 86400 if modified_days else 0
    hits = []
    for p in _walk(_roots(root)):
        low = p.name.lower()
        if words and not all(w in low for w in words):
            continue
        if exts and p.suffix.lower() not in {e.lower() for e in exts}:
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_size < min_size or st.st_mtime < since:
            continue
        hits.append((st.st_mtime, p))
    hits.sort(reverse=True)
    return [_info(p) for _, p in hits[: int(limit)]]


def recent(limit: int = 15, folder: str = "") -> list[dict]:
    """Recently changed files, newest first."""
    hits = []
    for p in _walk(_roots(folder)):
        try:
            hits.append((p.stat().st_mtime, p))
        except OSError:
            continue
    hits.sort(reverse=True)
    return [_info(p) for _, p in hits[: int(limit)]]


def read(path: str, summarise: bool = False, limit: int = 8000) -> dict:
    """The text of a document (text, code, Markdown, PDF, Word, OpenDocument) or a summary."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"{path} is not a file")
    ext = p.suffix.lower()
    if ext == ".pdf":
        text = proc.completed(["pdftotext", "-layout", str(p), "-"], timeout=60).stdout
    elif ext in (".docx", ".odt", ".pptx", ".odp"):
        with zipfile.ZipFile(p) as z:
            names = [
                n
                for n in z.namelist()
                if n in ("word/document.xml", "content.xml") or n.startswith("ppt/slides/slide")
            ]
            xml = " ".join(z.read(n).decode(errors="ignore") for n in sorted(names))
        text = re.sub(
            r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"</w:p>|</text:p>|</a:p>", "\n", xml))
        )
    else:
        text = p.read_text(errors="ignore")
    out = {"path": str(p), "characters": len(text)}
    if summarise:
        out["summary"] = llm.chat(
            "Summarise this document in at most 150 words of plain prose. Use only the document.",
            text[:14000],
        ).strip()
    else:
        out["text"] = text[: int(limit)]
    return out


def largest(folder: str = "~", limit: int = 12) -> dict:
    """The biggest folders directly inside a folder, and the biggest files below it."""
    base = Path(folder).expanduser()
    sizes = {}
    files = []
    for child in base.iterdir():
        if child.is_symlink():
            continue
        if child.is_dir():
            out = proc.completed(["du", "-sb", str(child)], timeout=300).stdout
            sizes[child.name] = int(out.split()[0]) if out else 0
        elif child.is_file():
            sizes[child.name] = child.stat().st_size
    for p in _walk([base], 200_000):
        try:
            files.append((p.stat().st_size, p))
        except OSError:
            continue
    files.sort(reverse=True)
    return {
        "folders": [
            {"name": n, "size_gb": round(s / 1e9, 2)}
            for n, s in sorted(sizes.items(), key=lambda x: -x[1])[: int(limit)]
        ],
        "files": [{"path": str(p), "size_gb": round(s / 1e9, 2)} for s, p in files[: int(limit)]],
    }


def duplicates(folder: str = "~/Downloads", min_size: str = "1mb", limit: int = 20) -> list[dict]:
    """Groups of identical files (same size and content) in a folder."""
    by_size: dict[int, list[Path]] = {}
    floor = _bytes(min_size)
    for p in _walk([Path(folder).expanduser()]):
        try:
            s = p.stat().st_size
        except OSError:
            continue
        if s >= floor:
            by_size.setdefault(s, []).append(p)
    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[str]] = {}
        for p in paths:
            h = hashlib.blake2b(digest_size=16)
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            by_hash.setdefault(h.hexdigest(), []).append(str(p))
        groups += [
            {"size_mb": round(size / 1e6, 1), "files": g} for g in by_hash.values() if len(g) > 1
        ]
    return sorted(groups, key=lambda g: -g["size_mb"] * len(g["files"]))[: int(limit)]


def tidy_downloads(folder: str = "~/Downloads", older_than_days: int = 0) -> dict:
    """Moves loose files in Downloads into folders by type (Documents, Images, Installers, ...)."""
    base = Path(folder).expanduser()
    cutoff = time.time() - int(older_than_days) * 86400
    moved: dict[str, int] = {}
    for p in base.iterdir():
        if not p.is_file() or p.name.startswith(".") or p.suffix in (".part", ".crdownload"):
            continue
        if older_than_days and p.stat().st_mtime > cutoff:
            continue
        kind = next(
            (k for k, exts in KINDS.items() if p.suffix.lower() in {e.lower() for e in exts}),
            "other",
        )
        dest_dir = base / kind.capitalize()
        dest_dir.mkdir(exist_ok=True)
        dest = dest_dir / p.name
        n = 2
        while dest.exists():
            dest = dest_dir / f"{p.stem} ({n}){p.suffix}"
            n += 1
        shutil.move(str(p), dest)
        moved[kind] = moved.get(kind, 0) + 1
    return {"moved": moved}


def folder_size(folder: str) -> dict:
    p = Path(folder).expanduser()
    out = proc.completed(["du", "-sb", str(p)], timeout=600).stdout
    return {"folder": str(p), "size_gb": round(int(out.split()[0]) / 1e9, 2) if out else None}
