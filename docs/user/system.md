# system

The `system` pack: system status, power, packages, devices, network, models and the shell. Each module below is a tool group with its own settings table.

## Install

```bash
hal packs add hal-system   # installs the pack into its own environment
hal packs list         # shows its modules and tools
```

Tool tiers and effects are in [the tool table](policy.md). Settings live in `~/.config/hal/config.toml`; each module section names its table.

## devices

hal-devices tells Hal what is plugged in and lets it use some of it: paired Bluetooth devices with
their battery, connecting headphones, USB devices, printers and printing a file, monitors and webcams.

### Highlights

- Bluetooth status, paired devices, connect, disconnect and power, through `bluetoothctl`.
- USB devices without the hubs, monitors with their resolution, and video devices.
- Printers, the default printer and the queue through CUPS; printing asks for confirmation.
- Short timeouts on every command, so a missing adapter returns an answer instead of hanging.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub devices_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-devices
python3 -m haldevices printers
python3 -m haldevices print_file path=~/Documents/ticket.pdf copies=1
python3 -m haldevices bluetooth_connect device=headphones
```

### Configuration

hal-devices has no settings.

## models

hal-models tells Hal about the local AI models: which are installed in Ollama, which are loaded and
how much GPU memory they take, and every program on the GPU. Hal can load, unload, download and
delete models, or ask a particular one a question.

### Highlights

- Installed models with size, family, parameters and quantisation.
- Loaded models with VRAM use and when they unload.
- The GPU's memory, use and temperature, with the name of each program (never its command line).
- Unload everything to free the GPU before a game or a training run.
- Deleting a model asks for confirmation.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub models_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-models
python3 -m halmodels loaded
python3 -m halmodels unload
python3 -m halmodels ask model=qwen3.5:9b prompt="Name three moons of Jupiter."
```

### Configuration

The Ollama address is `ollama_url` in the `[hal]` table of `~/.config/hal/config.toml`.

## network

hal-network tells Hal how the computer is connected and how well: connections, Wi-Fi, devices on the
local network, the public IP and provider, latency, open ports and a full speed test.

### Highlights

- Connection status from NetworkManager: devices, addresses, gateway, DNS servers and any VPN.
- Wi-Fi in use with signal strength, and the networks in range.
- Devices on the local network from the neighbour table, with names where they resolve.
- Ping, a check of whether a local port is open, and the programs listening on this machine.
- Download and upload speed and latency against Cloudflare's speed endpoints.
- Port checks refuse public addresses, so Hal never scans other people's machines.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub network_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-network
python3 -m halnet status
python3 -m halnet devices
python3 -m halnet speed_test megabytes=25
```

### Configuration

hal-network has no settings.

## packages

hal-packages tells Hal which software updates are waiting and where disk space has gone, and can
install updates or packages (through the desktop's password prompt) and empty the trash.

### Highlights

- Waiting updates from apt (security ones listed apart), snap and flatpak, and whether a restart is needed.
- Upgrades and installs through `pkexec`, so the password is typed into the desktop's own prompt,
  never given to Hal.
- Package search and an "is it installed" check covering apt, snap and commands on the `PATH`.
- A clean-up report of caches, trash, the system journal, Docker and old snap revisions, and
  emptying the trash and thumbnail cache.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub packages_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-packages
python3 -m halpkgs updates
python3 -m halpkgs installed name=wl-clipboard
python3 -m halpkgs cleanup_report
```

### Configuration

hal-packages has no settings.

## power

hal-power lets Hal suspend, restart or shut down the computer, now or after a delay, cancel a
scheduled shutdown, switch power profiles, and report the battery and uptime. Every action that ends
the session asks first.

### Highlights

- Suspend, restart and shutdown through systemd, with a delay in minutes if you want one.
- Scheduled shutdowns shown and cancelled.
- Power profiles through power-profiles-daemon: power-saver, balanced, performance.
- Battery charge where there is one, and uptime.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub power_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-power
python3 -m halpower profile mode=balanced
python3 -m halpower shutdown minutes=30
python3 -m halpower cancel_shutdown
```

### Configuration

hal-power has no settings.

## shell

hal-shell is Hal's fallback for anything the other modules do not cover: it runs shell commands.
`shell_look` runs one read-only program from a fixed table; `shell_run` is denied by default and the
hub asks you before every run.

### Highlights

- `shell_look` starts no shell. The command is split, the program must be on the table (`ls`, `cat`,
  `grep`, `find`, `df`, `ps`, `systemctl status`, `journalctl` and about fifty more), every option
  and argument must be allowed for that program, and it runs as an argv list from `/usr/bin`,
  `/bin`, `/usr/sbin` or `/sbin`.
- Pipes, redirects, chaining and substitution are refused. Use the `filter` argument to keep matching
  lines and `head` to keep the first lines.
- Every path argument and `cwd` is resolved (symlinks followed) and must be inside your home
  directory or `/tmp`, and outside `~/.ssh`, `~/.gnupg`, Hal's own config and state, `/proc`, `/sys`
  and `/dev`.
- The child runs in its own process group with no stdin and a minimal environment. Output is read up
  to `max_output` bytes, and the group is killed on a timeout or an overflow.
- `shell_run` runs any one program, also without a shell: `|`, `>` and `$VAR` reach the program as
  literal arguments. Its timeout is capped at `max_timeout_s`.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub shell_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-shell
python3 -m halshell look command="du -sh --max-depth=1 ~/Downloads" head=20
hal-hub shell_run command="mkdir -p ~/projects/new" --yes
```

### Configuration

Settings live in the `[shell]` table of `~/.config/hal/config.toml`:

```toml
[shell]
timeout_s = 20         # seconds a shell_look command may run
max_output = 65536     # bytes of output read
max_timeout_s = 600    # upper bound for a shell_run timeout
```

## system

hal-system tells Hal everything about the computer it runs on: hardware, CPU, memory, disks, GPU and
temperatures, what is running, which services have failed, and what the logs say went wrong.

### Highlights

- One-call overview: OS, uptime, CPU and memory use, GPU, disks and battery.
- Hardware inventory from `lscpu`, `lspci` and `lsblk`, with no root access needed.
- Temperatures from lm-sensors, `/sys` and the GPU.
- Processes by CPU or memory, and stopping one by id or exact program name (with confirmation).
  A stop never reaches Hal's own process or its parents.
- Failed system and user services, a service's state and recent log, and restarting it (with confirmation).
- Recent log errors from the system and user journals, merged.

### Use

The tools run from the module folder, or through hal-hub as `hal-hub system_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-system
python3 -m halsys overview
python3 -m halsys processes sort=memory limit=5
python3 -m halsys logs since="today" priority=err
python3 -m halsys services failed_only=true
```

### Configuration

hal-system has no settings.
