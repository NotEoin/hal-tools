"""Checks that the docs index lists every doc and that no page links to a missing file."""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
LINK = re.compile(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)")


def test_docs_index_lists_every_doc() -> None:
    index = (DOCS / "README.md").read_text()
    pages = {p.relative_to(DOCS).as_posix() for p in DOCS.rglob("*.md")} - {"README.md"}
    listed = set(LINK.findall(index))
    assert pages == listed, f"missing {sorted(pages - listed)}, unknown {sorted(listed - pages)}"


def test_doc_links_point_at_existing_files() -> None:
    for page in DOCS.rglob("*.md"):
        for target in LINK.findall(page.read_text()):
            assert (page.parent / target).is_file(), f"{page.name} links to missing {target}"
