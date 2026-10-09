# hal-habits

hal-habits tracks the small things: habits with a daily target and a streak (water, exercise,
reading, medication), how you feel, and how you slept. Tell Hal "I drank a glass of water" or "I
slept seven hours" and it is logged; an evening nudge lists what is still to do.

## Highlights

- Habits with daily targets in any unit, and streaks of days that met the target.
- Mood from 1 to 5 with notes, and sleep hours with quality.
- A seven-day view of habits met, mood and sleep.
- An evening nudge at 20:00 through hal-notify for habits not yet done.

## Install

hal-habits needs Python 3.11 or later.

```bash
git clone <url> ~/src/hal-ecosystem/hal-habits
ln -s ~/src/hal-ecosystem/hal-habits/systemd/* ~/.config/systemd/user/
systemctl --user enable --now hal-habits-nudge.timer
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub habits_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-habits
python3 -m halhabits create name=water target=8 unit=glasses
python3 -m halhabits log name=water
python3 -m halhabits mood score=4 note="good run"
python3 -m halhabits week
```

## Configuration

hal-habits has no settings; change the nudge time in `systemd/hal-habits-nudge.timer`.

## Licence

MIT. See [LICENSE](LICENSE).
