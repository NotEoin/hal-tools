# hal-media

hal-media lets Hal control whatever is playing (Spotify, a browser, VLC, Rhythmbox, any MPRIS player)
and play your own music by artist, album or song.

## Highlights

- What is playing in every open player: title, artist, album and position.
- Play, pause, next, previous, stop and seek, sent to the playing player or one you name.
- Local music found by words in its path, played in VLC (or the player you choose), shuffled if you like.
- YouTube searches and internet radio or podcast URLs.

## Install

hal-media needs Linux with a D-Bus session and the system Python with PyGObject (standard on GNOME
desktops). The hub runs it with `/usr/bin/python3`.

```bash
git clone <url> ~/src/hal-ecosystem/hal-media
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub media_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-media
/usr/bin/python3 -m halmedia status
/usr/bin/python3 -m halmedia control action=toggle
/usr/bin/python3 -m halmedia play_music query="radiohead ok computer" shuffle=true
```

## Configuration

Settings live in the `[media]` table of `~/.config/hal/config.toml`:

```toml
[media]
music_dirs = ["~/Music", "/media/music"]
player = "vlc"
```

## Licence

MIT. See [LICENSE](LICENSE).
