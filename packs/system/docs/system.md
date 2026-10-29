# hal-system

hal-system tells Hal everything about the computer it runs on: hardware, CPU, memory, disks, GPU and
temperatures, what is running, which services have failed, and what the logs say went wrong.

## Highlights

- One-call overview: OS, uptime, CPU and memory use, GPU, disks and battery.
- Hardware inventory from `lscpu`, `lspci` and `lsblk`, with no root access needed.
- Temperatures from lm-sensors, `/sys` and the GPU.
- Processes by CPU or memory, and stopping one by id or exact program name (with confirmation).
  A stop never reaches Hal's own process or its parents.
- Failed system and user services, a service's state and recent log, and restarting it (with confirmation).
- Recent log errors from the system and user journals, merged.

## Install

hal-system needs Python 3.11 or later on Linux with systemd. `lm-sensors` and `nvidia-smi` add
temperature and GPU readings when installed.

```bash
git clone <url> ~/src/hal-ecosystem/hal-system
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub system_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-system
python3 -m halsys overview
python3 -m halsys processes sort=memory limit=5
python3 -m halsys logs since="today" priority=err
python3 -m halsys services failed_only=true
```

## Configuration

hal-system has no settings.

## Licence

MIT. See [LICENSE](LICENSE).
