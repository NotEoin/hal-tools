# hal-devices

hal-devices tells Hal what is plugged in and lets it use some of it: paired Bluetooth devices with
their battery, connecting headphones, USB devices, printers and printing a file, monitors and webcams.

## Highlights

- Bluetooth status, paired devices, connect, disconnect and power, through `bluetoothctl`.
- USB devices without the hubs, monitors with their resolution, and video devices.
- Printers, the default printer and the queue through CUPS; printing asks for confirmation.
- Short timeouts on every command, so a missing adapter returns an answer instead of hanging.

## Install

hal-devices needs Python 3.11 or later on Linux; BlueZ for Bluetooth and CUPS for printing.

```bash
git clone <url> ~/src/hal-ecosystem/hal-devices
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub devices_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-devices
python3 -m haldevices printers
python3 -m haldevices print_file path=~/Documents/ticket.pdf copies=1
python3 -m haldevices bluetooth_connect device=headphones
```

## Configuration

hal-devices has no settings.

## Licence

MIT. See [LICENSE](LICENSE).
