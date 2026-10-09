# hal-network

hal-network tells Hal how the computer is connected and how well: connections, Wi-Fi, devices on the
local network, the public IP and provider, latency, open ports and a full speed test.

## Highlights

- Connection status from NetworkManager: devices, addresses, gateway, DNS servers and any VPN.
- Wi-Fi in use with signal strength, and the networks in range.
- Devices on the local network from the neighbour table, with names where they resolve.
- Ping, a check of whether a local port is open, and the programs listening on this machine.
- Download and upload speed and latency against Cloudflare's speed endpoints.
- Port checks refuse public addresses, so Hal never scans other people's machines.

## Install

hal-network needs Python 3.11 or later on Linux with NetworkManager and iproute2.

```bash
git clone <url> ~/src/hal-ecosystem/hal-network
```

## Use

The tools run from the module folder, or through hal-hub as `hal-hub network_<tool>`:

```bash
cd ~/src/hal-ecosystem/hal-network
python3 -m halnet status
python3 -m halnet devices
python3 -m halnet speed_test megabytes=25
```

## Configuration

hal-network has no settings.

## Licence

MIT. See [LICENSE](LICENSE).
