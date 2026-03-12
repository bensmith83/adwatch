# Tile Tracker

## Overview

Tile trackers advertise using BLE service UUID `0xFEED`. Tile is one of the original consumer Bluetooth trackers, predating Apple AirTag and Samsung SmartTag.

## BLE Advertisement Format

### Identification

- **AD Type:** `0x16` (Service Data — 16-bit UUID)
- **Service UUID:** `0xFEED` (Tile Inc.)
- **Source:** `service_data` dictionary, key `feed` or full 128-bit form

### What We Know

Tile advertisements are detected by the presence of service UUID `0xFEED` in service data. The internal payload structure is proprietary and not publicly documented in detail.

### What We Don't Parse

- Tile ID / device identifier encoding
- Battery level
- Tile model type (Mate, Pro, Slim, Sticker)
- Ringing state

## Identity Hashing

```
identifier = SHA256("{mac}:{service_data_hex}")[:16]
```

## Detection Significance

- Indicates a Tile tracker is nearby
- Cannot determine owner or specific Tile model from advertisement alone
- Tile trackers are common — expect background detections in public spaces

## Future Work

- Reverse-engineer Tile payload structure from captured advertisements
- Identify model type encoding (if present)
- Determine rotation behavior of Tile's BLE address

## References

- [Bluetooth SIG — Service UUID 0xFEED](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Tile Inc.)
