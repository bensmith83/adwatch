# Chipolo (Tracker Tag)

## Overview

Chipolo makes Bluetooth tracker tags similar to Tile. Older models broadcast with Chipolo-specific service UUIDs; newer models (ONE Spot, POP) use Apple Find My or Google Find My Device networks and will appear as Apple/Google accessories instead.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x08C3` (2243) | CHIPOLO d.o.o. |
| Service UUID | `0xFE33` | Newer Chipolo models |
| Service UUID (alt) | `451085d6-f833-4f77-83d4-4f9438894ed5` | Older Chipolo Classic/Plus |
| Local name | `Chipolo` | Older models only |

### Service Data Layout

Service data under the Chipolo UUID contains:

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | Color code | uint8 | Maps to physical tag color | — |

### Color Code Lookup

| Value | Color |
|-------|-------|
| 0 | Gray |
| 1 | White |
| 2 | Black |
| 3 | Violet |
| 4 | Blue |
| 5 | Green |
| 6 | Yellow |
| 7 | Orange |
| 8 | Red |
| 9 | Pink |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | Company ID / Service UUID | Chipolo tag nearby |
| Tag color | Service data[0] | Physical color of tag |

### What Requires GATT Connection

- Battery level
- Temperature (characteristic `0xFFF8`)
- Firmware version

### Apple Find My / Google FMD Variants

Newer Chipolo models (ONE Spot, POP) use Apple's Find My or Google's Find My Device network. These devices broadcast Apple (`0x004C`) or Google manufacturer data and will be caught by the existing `apple_findmy` or `google_fmd` parsers instead.

## Identity Hashing

```
identifier = SHA256("{mac}:chipolo")[:16]
```

## Detection Significance

- Popular tracker tag alternative to Tile/AirTag
- Color identification is a nice metadata bonus
- Older models have distinctive Chipolo-specific BLE identity
- Newer models piggyback on Apple/Google tracking networks

## References

- [Bluetooth SIG — Company ID 0x08C3](https://www.bluetooth.com/specifications/assigned-numbers/) — CHIPOLO d.o.o.
- [Bluetooth SIG — UUID 0xFE33](https://www.bluetooth.com/specifications/assigned-numbers/) — Chipolo service
