# Changelog

## Unreleased

### Changed

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
- `jobs`: while `[jobs]` is absent the old `jobhunt_root` default applies, with a one-time warning.
- Units are listed in each manifest as `[[units]]`, use `@PYTHON@`, and no longer carry machine paths
  or `hal-tts`. Only `hal-employment.service` is a GPU unit.

### Added

- Documentation index, per-pack user pages, how-tos and developer docs under `docs/`.
