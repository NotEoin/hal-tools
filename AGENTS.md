# Agent notes

hal-tools is a uv workspace of eight tool packs under `packs/`. Read
[docs/dev/architecture.md](docs/dev/architecture.md) first.

- Test: `uv run pytest` (hermetic). Lint: `uv run ruff check .` and `uv run ruff format --check .`.
  ASCII gate: `scripts/ascii-check.sh`.
- A tool needs a manifest entry, a row in `tests/tool-policy.csv` and tests, in one commit.
- Docs live in `docs/`; add new pages to `docs/README.md` (a test checks the index).
- Never put a personal path, address or account in code, docs or tests. Fixtures are synthetic.
- Every subprocess and network call has a timeout. Fetches use `halkit.netguard`.
- One-line commit subjects, no body, no trailers. Never push unless asked.
