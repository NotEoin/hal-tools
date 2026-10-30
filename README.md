# hal-tools

Tool packs for [Hal](https://github.com/NotEoin/Hal), the local-first assistant. Each pack
serves its tools to Hal, or to any MCP harness, with a tier and effects declared in a manifest so
the policy engine, not the tool, decides what runs.

| Pack | Tools |
| --- | --- |
| `organiser` | calendar, tasks, clock, notifications, briefings, routines |
| `life` | contacts, habits, ledger |
| `comms` | mail, phone, Telegram bridge |
| `online` | web search and reading, news feeds |
| `desktop` | desktop session, screen, media, RGB lighting |
| `system` | system status, power, packages, devices, network, models, shell |
| `work` | files, development, language tools |
| `jobs` | adapter to the Hal Employment app |

Status: work in progress, ported to the Hal 0.1 interfaces. Safe defaults: no mail account, no
personal paths, every fetch through the egress rules, every Telegram turn through `hal acp`.

## Install

```bash
hal packs add hal-organiser   # one pack, in its own environment
hal packs list                # modules and tools
```

To use a pack from another harness, see
[docs/howto/use-a-pack-from-any-harness.md](docs/howto/use-a-pack-from-any-harness.md).

## Run the tests

```bash
uv sync --all-packages    # needs hal-kit and hal-hub in ../Hal.next
uv run pytest             # hermetic tests only
```

More in [docs/dev/testing.md](docs/dev/testing.md). All documentation is indexed in
[docs/README.md](docs/README.md).

## Licence

MIT, see `LICENSE`. Security reports: see `SECURITY.md`.
