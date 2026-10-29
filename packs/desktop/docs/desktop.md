# hal-desktop

hal-desktop lets Hal work the GNOME desktop: start apps by name, open links and files, set the volume
and the speaker, switch dark mode and night light, change the wallpaper, use the clipboard, take
screenshots and lock the screen.

## Highlights

- Apps found by name, generic name or keyword across system, snap and flatpak `.desktop` files.
- Sound through PipeWire's `wpctl`: volume, nudges, mute, and switching the output device.
- Dark mode, night light, wallpaper and notification banners through `gsettings`.
- Screenshots through the xdg-desktop-portal, which works under Wayland without extra tools.
- The session: locked or not, idle time, lock now.

## Install

hal-desktop needs Python 3.11 or later, GNOME, PipeWire and PyGObject (installed with GNOME on
Ubuntu). The clipboard needs `wl-clipboard` (Wayland) or `xclip` (X11):

```bash
git clone <url> ~/src/hal-ecosystem/hal-desktop
sudo apt install wl-clipboard
```

The first screenshot may show GNOME's permission dialog; allow it once.

## Use

The tools run from the module folder, or through hal-hub as `hal-hub desktop_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-desktop
python3 -m haldesk launch app=firefox
python3 -m haldesk volume change=-10
python3 -m haldesk theme mode=dark
python3 -m haldesk screenshot
```

## Limitations

GNOME under Wayland gives other programs no way to list, move or focus windows, so hal-desktop has no
window tools. Monitor brightness on a desktop PC needs `ddcutil`.

## Configuration

hal-desktop has no settings. Screenshots are saved in `~/.local/share/hal/desktop/` unless a path is given.

## Licence

MIT. See [LICENSE](LICENSE).
