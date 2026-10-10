# hal-briefing

hal-briefing gives you a morning and an evening briefing: the weather, the day's calendar, tasks due,
the job search, headlines and anything wrong with the computer. Hal speaks it, pushes it to your
phone and writes it into the day's note in the vault.

## Highlights

- Gathers each part through hal-hub, so a module that is not installed is simply left out.
- Written to be spoken: short sentences, no lists or symbols.
- Morning: weather, today's events, tasks, job search, headlines, computer health.
- Evening: tomorrow's events, tasks still open, tomorrow's weather, job search.
- Midday: a short job-search update (`kind=jobs`), from hal-jobs.
- Timers for 08:05, 13:00 and 18:00, and on demand: "Hal, brief me." The morning one runs at 08:05
  so it falls after quiet hours (hal-notify's `quiet_until`, 08:00 by default) and is spoken.
- Waits for HAL's voice server when it is still starting after login, so the first briefing is heard.

## Install

hal-briefing needs Python 3.11 or later and hal-hub on the `PATH`; hal-notify delivers it. It lives
in `extensions/hal-briefing` and is installed by the ecosystem installer, which renders the units in
`systemd/` into `~/.config/systemd/user` (replacing `@ROOT@` with this folder) and starts them with
`hal.target`:

```bash
hal ext add briefing
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub briefing_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-briefing
python3 -m halbrief build kind=morning
python3 -m halbrief brief kind=evening speak=false
python3 -m halbrief build kind=jobs
```

## Configuration

Settings live in the `[briefing]` table of `~/.config/hal/config.toml`:

```toml
[briefing]
name = "Dave"      # how the briefing addresses you
```

Change the times by editing the timer units in `systemd/` and reinstalling them.

## Licence

MIT. See [LICENSE](LICENSE).
