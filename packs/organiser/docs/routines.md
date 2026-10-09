# hal-routines

hal-routines makes Hal proactive. A scene sets several things at once ("focus" silences
notifications, warms the lights, pauses music and starts a Pomodoro); schedules run a scene or any
tool at a time; triggers run one when something happens, such as the computer going idle or a USB
drive appearing.

## Highlights

- Built-in scenes: focus, relax, goodnight, away and movie, and any number you make by asking Hal.
- Steps are tool calls through hal-hub, so a scene can use every installed module, and a step whose
  module is missing is skipped without stopping the rest.
- Schedules in plain English: "every weekday at 8:45", "at 23:30".
- Triggers: idle, usb_added, offline, online, disk_full and login.
- Creating a scene, schedule or trigger asks for confirmation, because its steps later run unattended.

## Install

hal-routines needs Python 3.11 or later and hal-hub on the `PATH`.

```bash
git clone <url> ~/src/hal-ecosystem/hal-routines
ln -s ~/src/hal-ecosystem/hal-routines/systemd/hal-routines.service ~/.config/systemd/user/
systemctl --user enable --now hal-routines.service
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub routines_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-routines
python3 -m halroutines run name=focus
python3 -m halroutines schedule target=goodnight when_text="every day at 23:30"
python3 -m halroutines add_trigger event=usb_added target=notify_send args='{"title": "USB drive connected"}'
```

## Configuration

Settings live in the `[routines]` table of `~/.config/hal/config.toml`; built-in scenes can be
replaced there:

```toml
[routines]
idle_minutes = 15
[[routines.scenes.reading]]
tool = "rgb_colour"
args = { colour = "warm white", brightness = 60 }
```

## Licence

MIT. See [LICENSE](LICENSE).
