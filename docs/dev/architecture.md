# Architecture

hal-tools is a uv workspace of eight packs. Each pack is a Python distribution that holds several
tool modules. The packs depend on `hal-kit` (shared helpers) and `hal-hub` (the manifest, policy
and runner), both in `../Hal.next/packages`.

## Layout

| Path | What it holds |
| --- | --- |
| `packs/<pack>/pyproject.toml` | The distribution, its `hal.packs` entry points and its console script |
| `packs/<pack>/src/hal_<pack>/` | The pack CLI shim: `PACK`, `MODULES`, `main()` from `halhub.pack` |
| `packs/<pack>/src/hal<module>/` | One tool module: `tools.py`, `settings.py`, `hal-module.toml`, optional `systemd/`, `bin/`, `desktop/` |
| `packs/<pack>/tests/` | Hermetic tests for that pack |
| `tests/` | Cross-pack checks: manifests, policy table, units, docs, timeouts |
| `docs/` | User docs, how-tos and these developer docs |

## How a call flows

1. A harness or Hal core calls a tool name. The hub reads the manifest (`schema = 2`), which gives
   the tier, the effects and the typed parameters.
2. The policy engine decides from the manifest, never from the tool's own claim. Path and URL
   parameters are checked by the hub before the tool runs.
3. The runner starts the module in the pack's own environment and calls the function named in the
   manifest. Results come back as data; tool text from third parties is marked untrusted.
4. A module that needs another tool calls `halhub.client.call(tool, args, caller)`. It never
   shells out to the hub.

## Rules the code keeps

- Settings are one `halkit.config.Table` per module in `settings.py`. A bad file raises
  `ConfigError` with path and line; nothing is swallowed.
- Subprocesses go through `halkit.proc.run` (or a pack `proc` wrapper over it), with a timeout and
  an argv list, never a shell string. `tests/test_timeouts.py` scans for violations.
- Network fetches go through `halkit.netguard`, which applies the `[egress]` rules. The only
  direct sockets are the local model and the fixed Telegram API host.
- A tool narrows file access with its own roots through `halkit.paths.confine`; it never widens
  the hub's.
- Units live next to the manifest that lists them as `[[units]]`, use `@PYTHON@` and `@ROOT@`
  only, and carry no machine path. `tests/test_units.py` pins this.

## History

The 29 earlier extension repositories were imported with their history under `packs/<pack>/`.
`scripts/check-import.py` checks the import against the source repositories.
