# Contributing

1. Read [docs/dev/architecture.md](docs/dev/architecture.md) and
   [docs/dev/adding-a-tool.md](docs/dev/adding-a-tool.md).
2. Make one logical change per commit: code, tests and docs together. Every commit passes
   `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and
   `scripts/ascii-check.sh`.
3. Subjects are one line in the style of `git log --oneline`. No body, no trailers.
4. Add a CHANGELOG line for any user-visible change.
5. Open a pull request with a Summary of what changed and why, and a checklist: tests and lint green,
   docs updated, no secrets or generated files.

Text is plain ASCII. Secrets are never committed (`.gitleaks.toml` scans for them).
