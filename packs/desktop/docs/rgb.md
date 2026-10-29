# hal-rgb

hal-rgb lets Hal control your RGB lighting through OpenRGB: colours by name, brightness, built-in
effects, saved profiles, and lights that change with Hal's state (dim red at rest, bright red while
listening).

## Highlights

- A pure-Python client for the OpenRGB SDK protocol; no OpenRGB Python package needed.
- Colours by name ("warm white", "hal red", "light blue"), `#rrggbb` or `r,g,b`, at any brightness.
- Target everything or one kind of device by name: RAM, graphics card, motherboard.
- Effects by name where a device has them (rainbow, breathing, spectrum cycle), and saved profiles.
- `rgb_state` shows idle, listening, thinking, speaking and alert in configurable colours.

## Install

hal-rgb needs Python 3.11 or later and OpenRGB with its SDK server running. It lives in
`extensions/hal-rgb` and is installed by the ecosystem installer, which renders the units in
`systemd/` into `~/.config/systemd/user` (replacing `@ROOT@` with this folder) and starts them with
`hal.target`:

```bash
hal ext add rgb
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub rgb_<tool>`:

```bash
cd ~/src/hal-ecosystem/extensions/hal-rgb
python3 -m halrgb devices
python3 -m halrgb colour colour="warm white" brightness=40
python3 -m halrgb effect effect=rainbow device=gpu
python3 -m halrgb profile name=dark
```

## Configuration

Settings live in the `[rgb]` table of `~/.config/hal/config.toml`:

```toml
[rgb]
host = "127.0.0.1"
port = 6742
follow_device = ""           # lights that show Hal's state; empty means all
[rgb.states.listening]
colour = "hal red"
brightness = 100
```

## Licence

MIT. See [LICENSE](LICENSE).
