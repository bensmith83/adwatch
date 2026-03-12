# Efento (Environmental Sensors)

## Overview

Efento makes professional/industrial BLE environmental sensors with a well-documented two-frame advertisement protocol. They support temperature, humidity, pressure, CO2, and other measurements with optional encryption.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x026C` | Efento assigned |

### Two-Frame Protocol

Efento sensors broadcast data across two BLE frames (advertisement + scan response):

**Frame 1 — Advertisement:**

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | Version | uint8 | `0x03` for current protocol | — |
| 1-4 | Serial number | 4 bytes | Device serial | — |
| 5 | Measurement type 1 | uint8 | See sensor types table | — |
| 6-7 | Measurement value 1 | varies | Type-dependent | — |
| 8 | Measurement type 2 | uint8 | Second sensor slot | — |
| 9-10 | Measurement value 2 | varies | Type-dependent | — |
| 11 | Measurement type 3 | uint8 | Third sensor slot | — |
| 12-13 | Measurement value 3 | varies | Type-dependent | — |
| 14 | Battery | uint8 | Level indication | — |

**Frame 2 — Scan Response:**

| Field | Size | Notes |
|-------|------|-------|
| Firmware version | 2 bytes | Major.minor |
| Calibration date | 4 bytes | Unix timestamp |
| Extended data | varies | Model-specific |

### Sensor Type Codes

| Code | Sensor | Unit |
|------|--------|------|
| 0x01 | Temperature | °C |
| 0x02 | Humidity | % |
| 0x03 | Atmospheric pressure | hPa |
| 0x04 | Differential pressure | Pa |
| 0x05 | CO2 | ppm |
| 0x06 | PM1.0/2.5/10 | µg/m³ |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Up to 3 sensor readings | Frame 1 slots | Type-dependent decode |
| Device serial | Frame 1[1:5] | Stable identifier |
| Battery | Frame 1[14] | Level indication |
| Firmware version | Frame 2 | For device identification |

## Identity Hashing

```
identifier = SHA256("{mac}:{serial}")[:16]
```

## Detection Significance

- Industrial/commercial grade sensors
- More common in European markets
- Supports optional encryption (would need key for encrypted variants)
- Multi-sensor capability (up to 3 readings per device)

## References

- [Efento BLE Documentation](https://getefento.com/library/efento-bluetooth-low-energy-sensors-reading-advertising-data/) — Official protocol docs
