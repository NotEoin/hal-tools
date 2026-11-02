# hal-tools

> *Turn your local model into a desktop assistant.*

hal-tools gives [Hal](https://github.com/NotEoin/Hal) eight packs of tools. With them your local
model keeps your calendar and to-do list, reads your mail, talks to you over Telegram, searches the
web, controls your media and lights, and keeps an eye on your system. Every tool declares its tier
and effects in a manifest, so Hal's policy, not the tool, decides what runs, and anything risky
waits for you. Each pack also works from any MCP harness.

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

Defaults are conservative: no mail
account, no personal paths, every fetch through the egress rules, every Telegram turn through
`hal acp`.

## Part of the Hal suite

hal-tools is one part of [Hal](https://github.com/NotEoin/Hal), a modular AI assistant that runs on
your own machine, built privacy and security first. Around Hal,
[hal-memory](https://github.com/NotEoin/hal-memory) adds a memory,
[hal-voice](https://github.com/NotEoin/hal-voice) a voice,
[gpu-light](https://github.com/NotEoin/gpu-light) a fair share of the GPU, and
[hal-employment](https://github.com/NotEoin/hal-employment) a job-search helper. Each repo
works on its own; installed together they make one assistant. See [how it fits
together](https://github.com/NotEoin/Hal#how-it-fits-together).

## Requirements

- Linux, or Windows 11 through WSL2 ([how-to](docs/howto/run-on-windows-with-wsl2.md)). Native
  Windows and macOS are unsupported.
- Python 3.11 or later and [uv](https://docs.astral.sh/uv/).
- [Hal](https://github.com/NotEoin/Hal) to run the packs as Hal modules. Any MCP harness can use a
  pack alone.
- Some tools call system programs when you use them, such as `systemctl`, `wpctl`, `bluetoothctl`
  and `pdftotext`. A tool says which program is missing.

## Install

```bash
hal packs add hal-organiser   # one pack, in its own environment
hal packs list                # modules and tools
```

To use a pack from another harness, see
[docs/howto/use-a-pack-from-any-harness.md](docs/howto/use-a-pack-from-any-harness.md).

## Run

Hal starts the packs' tools and their systemd user units. To run a pack by hand:

```bash
hal-organiser doctor   # check the pack's config and tools
hal-organiser mcp      # serve its tools over MCP
```

Each pack's commands and settings are in its user page, listed in [docs/README.md](docs/README.md).

## Test

```bash
uv sync --all-packages    # needs the hal-kit and hal-hub packages of a Hal checkout at ../Hal.next
uv run pytest             # hermetic tests only
uv run ruff check . && uv run ruff format --check .
```

More in [docs/dev/testing.md](docs/dev/testing.md).

## Documentation

All documentation is indexed in [docs/README.md](docs/README.md).

## Licence

MIT, see `LICENSE`. Security reports: see `SECURITY.md`.
