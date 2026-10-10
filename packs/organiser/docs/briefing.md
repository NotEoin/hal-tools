# hal-briefing

hal-briefing gives you a morning and an evening briefing: the weather, the day's calendar, tasks due,
the job search, headlines and anything wrong with the computer. Hal speaks it, pushes it to your
phone and writes it into the day's note in the vault.

## Highlights

- Gathers each part through hal-hub, so a module that is not installed is simply left out.
- Written to be spoken: short sentences, no lists or symbols.
- Morning: weather, today's events, tasks, job search, headlines, computer health.
- Evening: tomorrow's events, tasks still open, tomorrow's weather, job search.
- Timers for 07:30 and 18:00, and on demand: "Hal, brief me."

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
```

## Configuration

Settings live in the `[briefing]` table of `~/.config/hal/config.toml`:

```toml
[briefing]
name = "Dave"      # how the briefing addresses you
```

Change the times by editing the two timer units.

## Licence

MIT. See [LICENSE](LICENSE).
