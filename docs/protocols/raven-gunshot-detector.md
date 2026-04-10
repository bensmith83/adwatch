# Raven Gunshot Detector (SoundThinking)

## Overview

The Raven is an acoustic gunshot detection sensor manufactured by SoundThinking (formerly ShotSpotter). Ravens are frequently co-deployed alongside Flock Safety ALPR cameras on utility poles and streetlights. They detect gunfire acoustically and report GPS-tagged events over cellular (LTE) backhaul.

Ravens broadcast BLE advertisements using the SoundThinking IEEE-registered OUI prefix `D4:11:D6`. When actively advertising GATT services, the advertised service UUIDs reveal device capabilities and can be used to estimate firmware version.

## BLE Advertisement Detection

### Primary Identification

| Field | Value | Notes |
|-------|-------|-------|
| MAC OUI Prefix | `D4:11:D6` | SoundThinking IEEE-registered OUI |
| Address Type | Public | Stable hardware MAC |

The OUI prefix is the primary passive detection method. No manufacturer-specific data company ID has been documented for Raven devices.

### GATT Service UUIDs

Ravens advertise some or all of the following service UUIDs depending on firmware version. These appear in BLE advertisement packets as well as being available via GATT connection.

#### Standard Services (FW 1.2+)

| Service | UUID (16-bit) | Full UUID | Data Exposed |
|---------|---------------|-----------|-------------|
| Device Info | `0x180A` | `0000180a-0000-1000-8000-00805f9b34fb` | Part number, serial, firmware, MAC |
| GPS | `0x3100` | `00003100-0000-1000-8000-00805f9b34fb` | Latitude, longitude, altitude |
| Power | `0x3200` | `00003200-0000-1000-8000-00805f9b34fb` | Battery voltage, solar voltage, charge current, board temp |
| Network | `0x3300` | `00003300-0000-1000-8000-00805f9b34fb` | LTE RSSI, RSRQ, RSRP, SINR, WiFi metrics |
| Uploads | `0x3400` | `00003400-0000-1000-8000-00805f9b34fb` | Audio upload timing and counts |
| Diagnostics | `0x3500` | `00003500-0000-1000-8000-00805f9b34fb` | Error counters: identity, heartbeat, OTA, audio failures |

#### Legacy Services (FW 1.1.x)

| Service | UUID (16-bit) | Full UUID | Data Exposed |
|---------|---------------|-----------|-------------|
| Health | `0x1809` | `00001809-0000-1000-8000-00805f9b34fb` | Temperature, battery, TX power |
| Location | `0x1819` | `00001819-0000-1000-8000-00805f9b34fb` | Latitude, longitude, altitude |

### Firmware Version Estimation

The firmware version can be estimated from the combination of advertised service UUIDs:

| Condition | Firmware Estimate |
|-----------|-------------------|
| Has `0x1819` (Location) but NOT `0x3100` (GPS) | **1.1.x** |
| Has `0x3100` (GPS) but NOT `0x3200` (Power) | **1.2.x** |
| Has `0x3100` (GPS) AND `0x3200` (Power) | **1.3.x** |
| No recognized service UUIDs | **unknown** |

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Device presence | MAC OUI prefix match (`D4:11:D6`) |
| Firmware estimate | Advertised service UUID combination |
| Available services | Mapped from advertised service UUIDs |
| Device name | BLE local name (when broadcast) |

## What Requires GATT Connection

All telemetry data requires an active BLE GATT connection to read:

- GPS coordinates (latitude, longitude, altitude)
- Battery voltage, solar status, charge current
- Board temperature
- LTE/WiFi signal metrics (RSSI, RSRQ, RSRP, SINR)
- Upload statistics
- Error/failure counters
- Device serial number and firmware version (exact)

## Identity Hashing

```
identifier = SHA256("raven:{mac_address}")[:16]
```

Uses `raven:` prefix (not `flock:`) for namespace separation since these are separate manufacturers.

## Detection Significance

- **Acoustic surveillance awareness**: Ravens continuously listen for gunfire and report to law enforcement, raising civil liberties concerns
- **GPS exposure**: Older firmware versions expose exact device GPS coordinates over unencrypted BLE GATT
- **Co-deployment indicator**: Raven presence strongly correlates with Flock Safety ALPR camera co-location
- **Infrastructure mapping**: Passive BLE detection enables mapping of acoustic sensor coverage areas
- **Unencrypted telemetry**: Battery, network, and error data are readable without authentication

## References

- [flock-you](https://github.com/colonelpanichacks/flock-you) — ESP32 Flock/Raven detector by colonelpanichacks
- [SoundThinking IEEE OUI](https://standards-oui.ieee.org/) — `D4:11:D6` registered to SoundThinking
- [flock-you datasets/raven_configurations.json](https://github.com/colonelpanichacks/flock-you/blob/main/datasets/raven_configurations.json) — Full GATT characteristic map across firmware versions
