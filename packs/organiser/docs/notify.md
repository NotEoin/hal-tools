# hal-notify

hal-notify routes Hal's alerts to the right places: your phone through ntfy, the desktop, HAL's
voice and Telegram. It respects quiet hours and do-not-disturb, lets urgent alerts through, and keeps
a history.

## Highlights

- One call reaches every channel you configure; each module that alerts uses it when it is installed.
- Quiet hours (22:00 to 08:00 by default) and do-not-disturb silence phone pushes and speech; urgent alerts still sound.
- Spoken alerts through old-home's `hal-say`, and Telegram through the chat old-home's bridge pairs.
- A history of every alert sent and the channels it reached.

## Install

hal-notify needs Python 3.11 or later and nothing from PyPI. For phone pushes, install the ntfy app
and subscribe to a long, random topic name.

```bash
git clone <url> ~/src/hal-ecosystem/hal-notify
```

## Use

The tools run from the module folder, or through hal-hub as `hal notify_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-notify
python3 -m halnotify send title="Build finished" body="All tests passed" speak=true
python3 -m halnotify dnd minutes=90
python3 -m halnotify state
python3 -m halnotify history limit=5
```

## Configuration

Settings live in the `[notify]` table of `~/.config/hal/config.toml`:

```toml
[notify]
ntfy_topic = "hal-a-long-random-name"
ntfy_server = "https://ntfy.sh"
channels = ["desktop", "phone"]     # add "voice" or "telegram" to use them by default
quiet_from = 22
quiet_until = 8
```

Anyone who knows the ntfy topic can read the alerts, so keep it unguessable.

## Licence

MIT. See [LICENSE](LICENSE).
