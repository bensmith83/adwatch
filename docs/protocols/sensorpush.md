# SensorPush (HT/HT.w/HTP)

## Overview

SensorPush makes premium BLE temperature/humidity sensors popular in wine cellars, server rooms, greenhouses, and cigar humidors. They publish an official Bluetooth API and broadcast readings in advertisement data.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `SensorPush` prefix | Device advertises with brand name |
| Manufacturer data | Present | Contains sensor readings |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Temperature | mfr_data | °C or °F depending on config |
| Humidity | mfr_data | Percentage |
| Battery | mfr_data | Level indication |

### What We Cannot Parse (requires GATT)

- Barometric pressure (HTP model only, via GATT characteristic)
- Historical log data
- Device configuration

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Premium sensor brand (~$50+ per unit)
- Continuous broadcasting for remote monitoring
- Common in specialized storage environments (wine, cigars, server rooms)

## References

- [SensorPush Bluetooth API](https://www.sensorpush.com/bluetooth-api) — Official documentation
