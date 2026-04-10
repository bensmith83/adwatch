# Flock Safety Surveillance Camera

## Overview

Flock Safety manufactures ALPR (Automatic License Plate Reader) cameras and related surveillance hardware deployed by law enforcement and HOAs across the US. Their devices broadcast BLE advertisements that can be passively detected, primarily from the "Penguin" battery packs and "FS Ext Battery" units that power the cameras.

adwatch detects Flock Safety hardware by matching the XUNTONG (`0x09C8`) BLE manufacturer company ID present in their advertisement packets. Additional classification is performed using BLE device names and known MAC address OUI prefixes.

## Device Types

| Device | BLE Name Pattern | Description |
|--------|-----------------|-------------|
| FS Ext Battery | `FS Ext Battery` | External battery pack, relays battery health over BLE |
| Penguin | `Penguin-XXXXXXXXXX` | Rechargeable battery pack (li-ion 10.8V 20Ah) |
| Pigvision | `Pigvision` | Camera module / processor unit |
| Flock (generic) | Contains `Flock` | Various Flock Safety hardware |
| Raven | Service UUID fingerprint | SoundThinking/ShotSpotter gunshot detector (co-deployed) |

## BLE Advertisement Format

### Identification

| Field | Value | Notes |
|-------|-------|-------|
| Company ID | `0x09C8` | XUNTONG — used by Flock Safety hardware |
| Local Name | `FS Ext Battery`, `Penguin-*`, `Pigvision`, `Flock*` | Case-insensitive match; not always present |
| AD Type | `0xFF` (Manufacturer Specific Data) | Standard BLE manufacturer data type |

### Manufacturer Data Layout

The manufacturer data begins with the XUNTONG company ID (`0x09C8`) in little-endian format, followed by a variable-length payload that includes device identification data such as serial numbers.

```
Byte 0-1: 0xC8 0x09  — Company ID (XUNTONG, little-endian)
Byte 2+:  payload     — Device-specific data (includes serial number)
```

**Example serial number format:** `TN72023022000771`

The internal payload structure varies by device type and firmware version. The serial number encoding is not fully documented — the payload is captured as raw hex for further analysis.

### Known BLE OUI Prefixes

These MAC address prefixes are associated with Flock Safety BLE devices (battery packs):

| OUI Prefix | Association |
|-----------|-------------|
| `EC:1B:BD` | FS Ext Battery / Penguin |
| `58:8E:81` | FS Ext Battery / Penguin |
| `90:35:EA` | FS Ext Battery / Penguin |
| `CC:CC:CC` | FS Ext Battery / Penguin |
| `B4:E3:F9` | FS Ext Battery / Penguin |
| `04:0D:84` | FS Ext Battery / Penguin |
| `F0:82:C0` | FS Ext Battery / Penguin |

### Known WiFi AP OUI Prefixes

Flock cameras also broadcast WiFi access points with SSID format `Flock-XXXXXX`. These MAC prefixes are associated with the WiFi modules (not parsed by this BLE plugin but useful for cross-referencing):

| OUI Prefix | Association |
|-----------|-------------|
| `D8:F3:BC` | Flock WiFi AP |
| `74:4C:A1` | Flock WiFi AP |
| `14:5A:FC` | Flock WiFi AP |
| `E4:AA:EA` | Flock WiFi AP |
| `3C:91:80` | Flock WiFi AP |
| `80:30:49` | Flock WiFi AP |
| `08:3A:88` | Flock WiFi AP |

## Raven Gunshot Detector (Co-deployed)

Flock Safety deploys SoundThinking (formerly ShotSpotter) "Raven" gunshot detectors alongside their ALPR cameras. Ravens advertise BLE GATT services that reveal device telemetry:

| Service | UUID (16-bit) | Data Exposed |
|---------|---------------|-------------|
| Device Info | `0x180A` | Part number, serial, firmware version, MAC |
| GPS | `0x3100` | Latitude, longitude, altitude |
| Power | `0x3200` | Board temp, battery voltage, charge current, solar voltage |
| Network | `0x3300` | LTE/WiFi RSSI, RSRQ, RSRP, SINR |
| Uploads | `0x3400` | Upload timing and counts |
| Failures | `0x3500` | Error counters (identity, status, heartbeat, OTA, audio) |

**Legacy services** (firmware 1.1.x): `0x1809` (Health), `0x1819` (Location)

Firmware version can be estimated from which service UUIDs are advertised:
- **1.1.x**: Legacy UUIDs (`0x1809`, `0x1819`)
- **1.2.x**: Standard service set (`0x180A`, `0x3100`–`0x3500`)
- **1.3.x**: Extended service set

> **Note:** Raven GATT services require an active connection to read. The current plugin only detects Flock hardware via passive BLE advertisement scanning (manufacturer data). Raven service UUID detection is documented here for future implementation.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Device type | BLE local name pattern matching |
| Known OUI flag | MAC prefix lookup against known Flock OUIs |
| Payload hex | Raw manufacturer data after company ID |
| Device name | BLE local name (when broadcast) |

## What Requires GATT Connection

- Raven GPS coordinates (latitude, longitude)
- Battery voltage, charge state, solar status
- LTE/WiFi signal metrics
- Device serial number (structured)
- Firmware version (exact)
- Error/failure counters

## Identity Hashing

```
identifier = SHA256("flock:{mac_address}")[:16]
```

MAC-based identity is used because Flock devices use stable (public) BLE addresses tied to their hardware.

## Detection Significance

- **Privacy/surveillance awareness**: Flock Safety cameras are ALPR devices that photograph and log every passing vehicle's license plate, storing data for law enforcement queries
- **Deployment mapping**: BLE detection enables passive mapping of camera locations without visual identification
- **Battery health monitoring**: The BLE advertisements from battery packs were originally designed for Flock's own maintenance — their presence enables third-party detection
- **Co-deployed hardware**: Where there's a Flock camera, there may also be a Raven gunshot detector broadcasting GPS coordinates and network status over unencrypted BLE GATT

## References

- [flock-you](https://github.com/colonelpanichacks/flock-you) — ESP32 Flock Safety camera detector by colonelpanichacks
- [flock-you-also](https://github.com/zebadrabbit/flock-you-also) — ESP32 Flock Safety device emulator with OUI and GATT data
- [oui-spy-unified-blue](https://github.com/colonelpanichacks/oui-spy-unified-blue) — Unified OUI-based surveillance device detector
- [ESP32 Marauder — Flock Sniff](https://github.com/justcallmekoko/ESP32Marauder/wiki/Flock-Sniff)
- [ESP32 Marauder — Flock Wardrive](https://github.com/justcallmekoko/ESP32Marauder/wiki/Flock-Wardrive)
- [DeFlock](https://deflock.me) — Crowdsourced Flock Safety camera database
