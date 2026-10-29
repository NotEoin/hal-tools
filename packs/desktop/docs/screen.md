# hal-screen

hal-screen lets Hal see: it takes a screenshot and asks a local vision model what is on the screen,
reads the text on it, or finds an error message and explains how to fix it. It can also look at any
image file.

## Highlights

- Screenshots through the xdg-desktop-portal, so it works under Wayland. GNOME refuses silent
  screenshots to unsandboxed programs, so the first attempt falls back to GNOME's Share dialog.
- A local vision model through Ollama (`qwen3-vl:8b` by default); nothing leaves the machine.
- Describe, read text, explain an error, or ask any question about an image file.
- Keeps only the newest screenshots (20 by default).

## Install

hal-screen needs the system Python with PyGObject, xdg-desktop-portal, and Ollama with a vision model:

```bash
git clone <url> ~/src/hal-ecosystem/hal-screen
ollama pull qwen3-vl:8b
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub screen_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-screen
/usr/bin/python3 -m halscreen describe question="Which app is in front?"
/usr/bin/python3 -m halscreen explain_error
/usr/bin/python3 -m halscreen describe_image path=~/Pictures/receipt.jpg question="What was the total?"
```

## Configuration

The vision model is `vision_model` in the `[hal]` table of `~/.config/hal/config.toml`; the
`[screen]` table holds `keep`, the number of screenshots kept.

## Licence

MIT. See [LICENSE](LICENSE).
