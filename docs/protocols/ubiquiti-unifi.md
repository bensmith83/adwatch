# Ubiquiti UniFi Wi-Fi Access Point

## Overview

Ubiquiti's UniFi line of Wi-Fi 6 / Wi-Fi 7 access points (U6-LR,
U6-Pro, U6-Lite, U6-Enterprise, U6-Mesh, U7-Pro, U7-Lite, …) emit a
small BLE advertisement continuously. Its main job is to support the
UniFi mobile app's "adopt nearby AP" workflow — the app uses the BLE
broadcast to recognize APs sitting next to the installer without
needing them to be on the network yet.

Even on fully-adopted APs the BLE radio keeps broadcasting, so
adwatch can passively recognize and identify every UniFi AP within
range. The payload exposes the **AP's Ethernet MAC** and an internal
counter; it does NOT expose client counts, throughput, or channel
data over BLE.

## Supported Models

Any UniFi AP that ships with a BLE radio. Confirmed via the local-name
field:

| Local name | Product |
|------------|---------|
| `U6-LR`    | UniFi 6 Long-Range |
| `U6-Pro`   | UniFi 6 Pro |
| `U6-Lite`  | UniFi 6 Lite |
| `U6-Mesh`  | UniFi 6 Mesh |
| `U6-Enterprise` | UniFi 6 Enterprise |
| `U7-Pro`   | UniFi 7 Pro |
| `U7-Lite`  | UniFi 7 Lite |

The parser does not gate on the local-name — older firmware sometimes
suppresses it — it only requires the Ubiquiti BLE service UUID and a
valid 6-byte MAC in service-data `0x252A`.

## BLE Advertisement Format

### Identification

```
Service UUID:  3E6E0806-6562-4A01-B6CD-E3409C5F9627
```

Custom 128-bit Ubiquiti service UUID, advertised on every payload.
Required for parser match.

### Service Data

| 16-bit UUID | Length | Meaning                                                  |
|-------------|--------|----------------------------------------------------------|
| `0x252A`    | 6      | AP Ethernet MAC (raw bytes, big-endian)                  |
| `0x2119`    | 4      | Monotonic counter (uptime ticks or boot counter, BE u32) |
| `0x2021`    | 1      | Adoption / state flag (`0x01` while broadcasting adoption invite) |

Example service-data block from a real U6-LR:

```
252A: 0c ea 14 80 11 dd      ← MAC 0c:ea:14:80:11:dd
2119: 00 0c 25 2b             ← counter 796459
2021: 01                      ← adoption flag set
```

The OUI `0C:EA:14` is registered to **Ubiquiti Inc.** — a useful
sanity check during forensic review.

### Counter Behavior

`0x2119` increments roughly once per second across consecutive
captures of the same AP. Two captures of the same physical AP a few
seconds apart will show a small positive delta; an unexpectedly
large jump (or a reset to a small value) suggests the AP rebooted.

### No Telemetry

The advertisement does NOT expose:

- SSID(s) or BSSIDs of active radios
- Client count, RSSI, or throughput
- Channel / band / Tx-power
- Firmware version

Those are all delivered via UniFi Network Application (cloud or
self-hosted) over a wired or 802.11 management interface.

## Identity Hashing

```
identifier_hash = SHA256("ubiquiti_unifi:{device_mac}")[:16]
```

The MAC in service-data `0x252A` is the AP's wired (Ethernet) MAC and
is **stable** — it does not rotate. Using it as the identity key
collapses all BLE-MAC-rotated sightings of the same AP into one
record.

## Why This Matters

- A passive scan in any neighborhood reveals every UniFi AP within
  range, exposing the deployment scale of a household / business
  even if the SSIDs are hidden.
- The counter delta yields a coarse uptime estimate — useful for
  spotting recently-rebooted infrastructure.
- The Ubiquiti OUI on the embedded MAC differentiates legitimate
  UniFi gear from look-alike devices.

## References

- Ubiquiti BLE adoption workflow: https://help.ui.com/hc/en-us/articles/204910064
- UniFi product line: https://store.ui.com/us/en/category/all-wifi
- OUI lookup: https://standards-oui.ieee.org/oui/oui.txt (`0C-EA-14`)
