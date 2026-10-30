# desktop

The `desktop` pack: the desktop session, screen, media and RGB lighting. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-desktop   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## desktop

hal-desktop lets Hal work the GNOME desktop: start apps by name, open links and files, set the volume
and the speaker, switch dark mode and night light, change the wallpaper, use the clipboard, take
screenshots and lock the screen.

### Highlights

- Apps found by name, generic name or keyword across system, snap and flatpak `.desktop` files.
- Sound through PipeWire's `wpctl`: volume, nudges, mute, and switching the output device.
- Dark mode, night light, wallpaper and notification banners through `gsettings`.
- Screenshots through the xdg-desktop-portal, which works under Wayland without extra tools.
- The session: locked or not, idle time, lock now.

### Use

Run a tool with `hal-desktop call desktop_<tool>`:

```bash
hal-desktop call desktop_launch app=firefox
hal-desktop call desktop_volume change=-10
hal-desktop call desktop_theme mode=dark
hal-desktop call desktop_screenshot
```

### Limitations

GNOME under Wayland gives other programs no way to list, move or focus windows, so hal-desktop has no
window tools. Monitor brightness on a desktop PC needs `ddcutil`.

### Configuration

hal-desktop has no settings. Screenshots are saved in `~/.local/share/hal/desktop/` unless a path is given.

## media

hal-media lets Hal control whatever is playing (Spotify, a browser, VLC, Rhythmbox, any MPRIS player)
and play your own music by artist, album or song.

### Highlights

- What is playing in every open player: title, artist, album and position.
- Play, pause, next, previous, stop and seek, sent to the playing player or one you name.
- Local music found by words in its path, played in VLC (or the player you choose), shuffled if you like.
- YouTube searches and internet radio or podcast URLs.

### Use

Run a tool with `hal-desktop call media_<tool>`:

```bash
hal-desktop call media_status
hal-desktop call media_control action=toggle
hal-desktop call media_play_music query="radiohead ok computer" shuffle=true
```

### Configuration

Settings live in the `[media]` table of `~/.config/hal/config.toml`:

```toml
[media]
music_dirs = ["~/Music", "/media/music"]
player = "vlc"
```

## rgb

hal-rgb lets Hal control your RGB lighting through OpenRGB: colours by name, brightness, built-in
effects, saved profiles, and lights that change with Hal's state (dim red at rest, bright red while
listening).

### Highlights

- A pure-Python client for the OpenRGB SDK protocol; no OpenRGB Python package needed.
- Colours by name ("warm white", "hal red", "light blue"), `#rrggbb` or `r,g,b`, at any brightness.
- Target everything or one kind of device by name: RAM, graphics card, motherboard.
- Effects by name where a device has them (rainbow, breathing, spectrum cycle), and saved profiles.
- `rgb_state` shows idle, listening, thinking, speaking and alert in configurable colours.

### Use

Run a tool with `hal-desktop call rgb_<tool>`:

```bash
hal-desktop call rgb_devices
hal-desktop call rgb_colour colour="warm white" brightness=40
hal-desktop call rgb_effect effect=rainbow device=gpu
hal-desktop call rgb_profile name=dark
```

### Configuration

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

## screen

hal-screen lets Hal see: it takes a screenshot and asks a local vision model what is on the screen,
reads the text on it, or finds an error message and explains how to fix it. It can also look at any
image file.

### Highlights

- Screenshots through the xdg-desktop-portal, so it works under Wayland. GNOME refuses silent
  screenshots to unsandboxed programs, so the first attempt falls back to GNOME's Share dialog.
- A local vision model through Ollama (`qwen3-vl:8b` by default); nothing leaves the machine.
- Describe, read text, explain an error, or ask any question about an image file.
- Keeps only the newest screenshots (20 by default).

### Use

Run a tool with `hal-desktop call screen_<tool>`:

```bash
hal-desktop call screen_describe question="Which app is in front?"
hal-desktop call screen_explain_error
hal-desktop call screen_describe_image path=~/Pictures/receipt.jpg question="What was the total?"
```

### Configuration

Screen questions go to the Hal gateway chat model (`hal-chat`), which must accept images. The
`[screen]` table holds `keep`, the number of screenshots kept.
