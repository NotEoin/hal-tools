# hal-power

hal-power lets Hal suspend, restart or shut down the computer, now or after a delay, cancel a
scheduled shutdown, switch power profiles, and report the battery and uptime. Every action that ends
the session asks first.

## Highlights

- Suspend, restart and shutdown through systemd, with a delay in minutes if you want one.
- Scheduled shutdowns shown and cancelled.
- Power profiles through power-profiles-daemon: power-saver, balanced, performance.
- Battery charge where there is one, and uptime.

## Install

hal-power needs Python 3.11 or later on a systemd Linux desktop.

```bash
git clone <url> ~/src/hal-ecosystem/hal-power
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub power_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-power
python3 -m halpower profile mode=balanced
python3 -m halpower shutdown minutes=30
python3 -m halpower cancel_shutdown
```

## Configuration

hal-power has no settings.

## Licence

MIT. See [LICENSE](LICENSE).
