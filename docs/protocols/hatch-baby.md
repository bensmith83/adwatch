# Hatch Baby (Sound Machine / Night Light)

## Overview

Hatch Baby Rest sound machines and night lights broadcast BLE advertisements for control via the Hatch Sleep app. They are identified by their `local_name` (e.g. "Bedroom Hatch") and custom service UUIDs. Hatch devices use Nordic Semiconductor's BLE stack and include DFU (Device Firmware Update) capability.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | User-assigned name + " Hatch" or "Hatch Rest" | e.g. `Bedroom Hatch` |
| Service UUID (advertised) | `00001530-1212-efde-1523-785feabcd123` | Nordic DFU Service |
| Service UUID (advertised) | `02240001-5efd-47eb-9c1a-de53f7a2b232` | Hatch custom service |
| Service UUID (advertised) | `02260001-5efd-47eb-9c1a-de53f7a2b232` | Hatch custom service |

The Nordic DFU service UUID (`00001530-1212-efde-1523-785feabcd123`) is common to many Nordic-based IoT devices, but the combination with Hatch-specific UUIDs (`0224xxxx`, `0226xxxx`) is distinctive.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name or service_uuids | Hatch device nearby |
| User-assigned name | local_name | e.g. "Bedroom" from "Bedroom Hatch" |
| Nordic DFU capable | service_uuid `00001530-...` | Firmware update support |

### What We Cannot Parse (requires GATT)

- Device model (Rest, Rest+, RestNoSD, etc.)
- Firmware version
- Hardware revision
- Battery level
- Current sound/light settings

## Local Name Pattern

Hatch devices use user-assigned names from the app, followed by " Hatch":

```
{room_name} Hatch
```

Examples: `Bedroom Hatch`, `Nursery Hatch`, `Living Room Hatch`

This means the local_name reveals room placement — useful for spatial context.

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Hatch devices likely use a static or semi-static BLE MAC, making this a stable identifier.

## Known Models

| Model | Product | Notes |
|-------|---------|-------|
| RestNoSD | Hatch Rest (no SD card) | Original sound machine |
| Rest+ | Hatch Rest+ | WiFi + BLE model |
| Rest 2nd Gen | Hatch Rest 2nd Gen | Latest generation |

## Detection Significance

- Baby/child monitoring device — strong indicator of a nursery or family environment
- User-assigned name reveals room placement
- Broadcasts continuously for app control (always-on BLE)
- Nordic DFU service indicates OTA firmware update capability

## Future Work

- Determine if manufacturer_data contains model or state information
- Check if advertisement changes when sound/light is active vs. off
- Map the `0224xxxx` and `0226xxxx` UUID ranges to specific features

## References

- [Hatch Sleep](https://www.hatch.co/) — manufacturer website
