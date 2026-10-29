# hal-clock

hal-clock gives Hal timers, alarms, a stopwatch and Pomodoro sessions. When one goes off, Hal says
so aloud and the alert reaches your phone and desktop, even during quiet hours.

## Highlights

- Timers with names and natural lengths: "9 minutes", "1h30", "an hour and a half", "2:30".
- Alarms at a time, one-off or repeating ("7 tomorrow morning", "every weekday at 7"), and snooze. A
  bare hour is the morning: "at 7" wakes you at 07:00.
- A stopwatch with laps, and Pomodoro sessions that announce each break and return to work.
- A one-second daemon, so timers fire on time; state lives in SQLite and survives restarts.

## Install

hal-clock needs Python 3.11 or later; alerts go through hal-notify when it is installed. It lives in
`extensions/hal-clock` and is installed by the ecosystem installer, which renders the units in
`systemd/` into `~/.config/systemd/user` (replacing `@ROOT@` with this folder) and starts them with
`hal.target`:

```bash
hal ext add clock
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub clock_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-clock
python3 -m halclock timer duration="9 minutes" label=pasta
python3 -m halclock alarm when_text="every weekday at 7am" label="Wake up"
python3 -m halclock pomodoro action=start work=25 rest=5 rounds=4
python3 -m halclock list
```

## Configuration

hal-clock has no settings of its own; alerts follow hal-notify's channels.

## Licence

MIT. See [LICENSE](LICENSE).
