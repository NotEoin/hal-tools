# Run on Windows with WSL2

This page shows how to run the hal-tools packs on a Windows 11 PC through WSL2, and which tools
work there. Native Windows and macOS are not supported: the packs read `/proc` and `/sys`, call
`systemctl`, `gsettings` and `wpctl`, and use UNIX sockets. WSL2 runs a real Linux kernel, so it
is the supported route.

Support is new and has not been run on a Windows PC yet. The table after the steps marks each
pack as verified or unverified.

## Steps

1. Enable WSL and install Ubuntu. In an administrator PowerShell on Windows:

   ```powershell
   wsl --install -d Ubuntu-24.04   # installs WSL2 and the distro; reboot when asked
   wsl --update                    # WSLg (windows, clipboard, sound) ships with WSL
   wsl --status                    # Default Version: 2
   ```

2. Enable systemd inside the distro. The timers and daemons of the packs (briefings, reminders,
   routines, the Telegram bridge) are systemd user units. Inside Ubuntu:

   ```bash
   printf '[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf   # edit by hand if [boot] exists
   ```

   ```powershell
   wsl --shutdown   # run in PowerShell; stops every WSL distro, then reopen Ubuntu
   ```

   ```bash
   systemctl --user is-system-running   # running or degraded, not "offline"
   ```

3. Keep your files in the Linux filesystem. A path under `/mnt/c` is slow, and has no Unix
   permissions, so the file tools and `shell_look` are slow there (unverified: the permission
   checks may also see wide-open modes).

   ```bash
   cd ~ && pwd   # /home/<you>, inside the distro's own disk
   ```

4. Install Hal and the packs you want, inside Ubuntu. See the Hal README for Hal itself.

   ```bash
   hal packs add hal-organiser   # one pack, in its own environment
   hal packs list                # modules and tools
   ```

5. Optional: the packs that talk to a desktop need WSLg. Check that it is on.

   ```bash
   echo "$DISPLAY $WAYLAND_DISPLAY"   # :0 and wayland-0 when WSLg is on
   ```

6. Optional: an NVIDIA GPU. Install the driver on Windows, not in Ubuntu. Then `nvidia-smi`
   works inside Ubuntu, and the `system` pack's GPU tools read it.

   ```bash
   nvidia-smi   # lists your GPU; if not, update the Windows driver
   ```

## What works under WSL2

"Unverified" means the design expects it to work, but nobody has run it on WSL2. Run the check
in the last column and report the result.

| Feature | Status | How to check |
| --- | --- | --- |
| Platform check (`osrelease` says `microsoft` or `WSL`) | Verified with a fake `osrelease` in the test suite | `uv run pytest packs/system/tests/test_power.py` |
| Hermetic test suite | Wired into CI on a Windows runner; not yet seen green | The `wsl` job of the CI workflow |
| `power_suspend`, `power_restart`, `power_shutdown`, `power_profile` | Refuse with advice under WSL2; verified with a fake `osrelease` | Ask Hal to run one; it answers that WSL2 has no power state |
| `desktop_lock` | Refuses with advice under WSL2; verified with a fake `osrelease` | Ask Hal to lock the screen |
| Volume and audio devices (`wpctl`) | Report a clear error when `wpctl` is missing, which is normal under WSLg (it serves PulseAudio); verified with a fake lookup | Ask Hal for the volume |
| `system` status: memory, CPU, disks, processes, uptime | Unverified; reads `/proc`, which WSL2 provides | `system_overview` |
| Battery, temperatures, board name | Unverified; WSL2 has no `/sys/class/power_supply`, thermal zones or DMI, and the tools already report "mains power" or leave the field out | `system_overview` |
| Bluetooth, monitors, cameras | Unverified; WSL2 exposes none of them to Linux, and the tools report none | `devices_*` tools |
| GPU tools (`nvidia-smi`) | Unverified; per-process memory may print `[N/A]` | `nvidia-smi --query-gpu=memory.used --format=csv` |
| systemd user timers and daemons | Unverified; need `systemd=true` in `/etc/wsl.conf` | `systemctl --user list-timers` |
| Desktop notifications (`notify-send`) | Unverified; they need a notification daemon, which WSLg does not run. Without one, the Telegram pairing code is logged instead | `notify-send test` |
| Clipboard (`wl-copy`, `xclip`) | Unverified; WSLg shares the Windows clipboard | `echo hi \| wl-copy`, then paste in Windows |
| Screen capture (`screen_*`) | Unverified; needs the xdg-desktop-portal, which WSLg does not run | Ask Hal to look at the screen |
| Media control (MPRIS) | Unverified; Windows players are not on the Linux session bus | `media_*` tools with a Linux player in WSLg |
| RGB lighting (OpenRGB) | Unverified; USB devices are not passed through to WSL2 by default | `openrgb --list-devices` |
| Mail, calendar, tasks, contacts, ledger, web, feeds, jobs | Unverified on WSL2; they use files and the network only | The pack's smoke tools, for example `tasks_list` |

## Symptoms and fixes

| Symptom | Fix |
| --- | --- |
| A power tool says it is not available under WSL2 | Intended. Use `wsl --shutdown` in PowerShell to stop WSL, or Windows' own power menu. |
| `desktop_lock` says there is no desktop session | Intended. Lock Windows with Win+L. |
| Volume tools say `wpctl` is not installed | WSLg serves PulseAudio. Control the volume in Windows, or use `pactl` yourself. |
| Timers and reminders never fire | systemd is off. Do step 2, then `wsl --shutdown`. |
| `systemctl --user` says `Failed to connect to bus` | Do step 2, or run `loginctl enable-linger "$USER"` and `wsl --shutdown`. |
| The Telegram pairing code does not pop up | No notification daemon runs in WSLg. Read the code in the bridge log: `journalctl --user -u hal-telegram`. |
| File tools are slow | The files are under `/mnt/c`. Copy them into `~`. |
| `system_overview` has no battery or temperature | WSL2 does not expose them. Check the host in Windows. |
| `nvidia-smi` is not found in Ubuntu | Install or update the NVIDIA driver on Windows, then `wsl --shutdown`. Do not install a Linux driver in the distro. |
| A tool answers `Failed to connect to bus` or has no display | Check `echo $DISPLAY`. If empty, run `wsl --update` in PowerShell and `wsl --shutdown`. |
