# Testing

The default run is hermetic: no network, no GPU, no desktop session, no real home directory.

```bash
uv sync --all-packages    # needs hal-kit and hal-hub in ../Hal
uv run pytest             # hermetic tests only
uv run ruff check .       # lint
uv run ruff format --check .   # formatting
scripts/ascii-check.sh    # no tracked file may contain non-ASCII, except those in .ascii-allow
```

To match CI, run pytest under a clean environment:

```bash
env -i HOME="$(mktemp -d)" PATH="$PATH" uv run pytest   # no inherited variables, empty home
```

## Markers

Tests that need real infrastructure carry a marker and are skipped by default
(`addopts` in `pyproject.toml`). Run one kind with `-m`:

| Marker | Needs |
| --- | --- |
| `host` | A desktop session or real host services |
| `network` | Internet access |
| `gpu` | A GPU |
| `docker` | A Docker daemon |
| `slow` | More than 10 seconds |
| `bwrap` | bubblewrap |
| `systemd` | A systemd user session |
| `live` | A real model server |

## Conventions

- Test names are behaviour sentences: `test_expired_token_is_refreshed_once`.
- A regression test names the bug it guards against.
- Tests live in `packs/<pack>/tests/test_<module>.py`; cross-pack checks live in `tests/`.
- Fixtures are synthetic. Model servers, bots and agents are fakes (for example a scripted
  `hal acp` on a socketpair for the Telegram bridge).
- `tests/tool-policy.csv` must match the manifests; change both in one commit.
