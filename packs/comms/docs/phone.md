# hal-phone

hal-phone connects Hal to your phone through KDE Connect: ring it when it is lost, check its battery,
send it files, links and text, read its notifications, and send a text message from it.

## Highlights

- "Hal, where's my phone?" rings it at full volume.
- Files, links and text sent from the computer to the phone.
- The phone's notifications and battery level.
- SMS from the phone's own number; Hal asks before sending.

## Install

hal-phone needs Python 3.11 or later, KDE Connect on the computer (GSConnect also works on GNOME) and
the KDE Connect app on the phone:

```bash
git clone <url> ~/src/hal-ecosystem/hal-phone
sudo apt install kdeconnect
kdeconnect-cli --list-available      # then pair from the phone app
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub phone_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-phone
python3 -m halphone ring
python3 -m halphone send_file path=~/Documents/ticket.pdf
```

## Configuration

Settings live in the `[phone]` table of `~/.config/hal/config.toml`:

```toml
[phone]
phone = "Pixel"      # which paired device to use when there are several
```

## Licence

MIT. See [LICENSE](LICENSE).
