# hal-packages

hal-packages tells Hal which software updates are waiting and where disk space has gone, and can
install updates or packages (through the desktop's password prompt) and empty the trash.

## Highlights

- Waiting updates from apt (security ones listed apart), snap and flatpak, and whether a restart is needed.
- Upgrades and installs through `pkexec`, so the password is typed into the desktop's own prompt,
  never given to Hal.
- Package search and an "is it installed" check covering apt, snap and commands on the `PATH`.
- A clean-up report of caches, trash, the system journal, Docker and old snap revisions, and
  emptying the trash and thumbnail cache.

## Install

hal-packages needs Python 3.11 or later on a Debian or Ubuntu system.

```bash
git clone <url> ~/src/hal-ecosystem/hal-packages
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub packages_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-packages
python3 -m halpkgs updates
python3 -m halpkgs installed name=wl-clipboard
python3 -m halpkgs cleanup_report
```

## Configuration

hal-packages has no settings.

## Licence

MIT. See [LICENSE](LICENSE).
