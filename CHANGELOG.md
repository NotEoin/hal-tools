# Changelog

## Unreleased

### Added

- WSL2 support: `power_suspend`, `power_restart`, `power_shutdown` and `power_profile` refuse with
  advice under WSL2, `desktop_lock` says there is no session to lock, and the volume tools say when
  `wpctl` is missing. `HAL_TOOLS_OSRELEASE` fakes the kernel release in tests. New how-to:
  `docs/howto/run-on-windows-with-wsl2.md`. A `wsl` CI job runs the hermetic suite.

### Fixed

- The `rgb_*` tools declare network. They talk to OpenRGB's SDK server on 127.0.0.1:6742, and
  a tool without network runs in its own network namespace under Hal's sandbox, so every call
  failed with "OpenRGB's SDK server is not running" while it was.
- The `hal-telegram` unit starts the bridge (`python -m haltelegram.cli`). Before, it ran
  `python -m haltelegram`, which printed the pack usage and restarted every 15 seconds.
- `jobs_open` asks the desktop's OpenURI portal (over the session bus, with `gdbus`) to open Hal
  Employment. Before, it started `gio open` inside Hal's tool sandbox, where the browser died with
  the sandbox, and it reported success anyway. It now raises when the portal refuses or `gdbus`
  is missing, naming the URL to open by hand.

### Changed

- README lists requirements, install, run and test; example paths in the user pages no longer use a `Documents` folder.
- `jobs_mark`, `jobs_shortlist`, `jobs_todo_add` and `jobs_stats` mark their output untrusted, like
  the other jobs tools: it echoes company, title and to-do text taken from job pages and emails.
- `jobs_queue` and `jobs_applications` read the Hal Employment command line only. The web API they
  tried first no longer exists, and `[jobs].employment_url` now only sets what `jobs_open` opens.
- `shell_look` reads the roots in `[tools.shell_look].read_roots` (else `[paths].read_roots`) through
  the hub's path rule, so its hard-deny list and workspace rule apply. It no longer defaults to the
  whole home directory and `/tmp`.
- `routines_schedule` and `routines_add_trigger` take `steps` (JSON) and a required `label` instead
  of `target` and `args`. All three save tools are tier `act` and ask; approval creates a routine
  grant for the exact steps. The routines daemon runs unattended under those grants, skips other
  steps that need approval and notifies once, and refuses to start when the hub is not reachable.
- `routines`: scene steps no longer carry `_confirmed`. Each step is its own hub call, so policy
  decides it; a step that needs approval is reported as `skipped`. `routines_run` is tier `write`
  and allowed; it adds no authority.
- `notify` and every pack that alerts now use `halkit.notify`; the `telegram` alert channel is gone and
  voice alerts use `[notify].say_command`. Model calls go through `halkit.llm` (the Hal gateway),
  so the `ollama_url`, `chat_model`, `vision_model` and `gpu_ignore` settings no longer apply to
  these packs.
- Telegram: the bridge is an ACP client of `hal acp --channel telegram --toolset assistant`. Tool
  approvals arrive as inline buttons; link previews are off; voice notes use the `hal-voice` CLI.
  The `persona`, `model`, `whisper_*` and `voice_root` keys are gone; `turn_timeout_s` is new.
- Telegram pairing codes expire after 10 minutes and five wrong codes in 10 minutes lock pairing
  until the bridge restarts.
- `mail`: there is no built-in account. Add `[mail.accounts.<name>]`; see
  [docs/howto/add-a-mail-account.md](docs/howto/add-a-mail-account.md).
- `web` and `feeds`: every fetch goes through the egress rules, with the shared `[net]` table. A
  stored `http` feed is skipped.
- `files`, `dev` and `calendar` confine paths. New key `[calendar].import_roots`. Default `[dev].roots`
  is `~/src` and `~/projects`; missing folders are skipped.
- `desktop_clipboard` takes no arguments; writing is the new `desktop_clipboard_set` (asks).
- `desktop_open` takes `url` (https only) or `path`, exactly one.
- `system_processes` and `models_gpu` return process names only, never command lines.
- `jobs`: `[jobs].jobhunt_root` has no default; the launcher exits with a message naming it when unset.
- Units are listed in each manifest as `[[units]]`, use `@PYTHON@`, and no longer carry machine paths
  or `hal-tts`. Only `hal-employment.service` is a GPU unit.

### Added

- Documentation index, per-pack user pages, how-tos and developer docs under `docs/`.
