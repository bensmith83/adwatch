# BlueMaestro Tempo Disc

## Overview

BlueMaestro Tempo Disc sensors are professional-grade environmental monitors. The manufacturer officially publishes their BLE advertisement format, making this one of the best-documented BLE sensor protocols.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | BlueMaestro-specific | Check BLE SIG assigned numbers |
| Local name | `T`, `TD` prefix patterns | e.g. `T30`, `TD20` |

### Manufacturer Data Layout (officially published)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | Version | uint8 | Protocol version | — |
| 1 | Battery | uint8 | Raw value | % |
| 2-3 | Current temperature | int16 | `value / 10` (signed) | °C |
| 4-5 | Current humidity | uint16 | `value / 10` | % |
| 6-7 | Current dew point | int16 | `value / 10` (signed) | °C |
| 8-9 | Max temperature | int16 | `value / 10` (signed) | °C |
| 10-11 | Min temperature | int16 | `value / 10` (signed) | °C |
| 12-13 | Max humidity | uint16 | `value / 10` | % |
| 14-15 | Min humidity | uint16 | `value / 10` | % |
| 16-17 | Logging interval | uint16 | Raw value | seconds |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Temperature | mfr_data[2:4] | °C, signed, /10 |
| Humidity | mfr_data[4:6] | %, /10 |
| Dew point | mfr_data[6:8] | °C, signed, /10 |
| Battery | mfr_data[1] | Percentage |
| Min/max temp | mfr_data[8:12] | Historical extremes |
| Min/max humidity | mfr_data[12:16] | Historical extremes |
| Logging interval | mfr_data[16:18] | Seconds between samples |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Professional-grade sensors used in labs, wine cellars, server rooms
- Officially documented protocol (rare for BLE devices)
- Broadcasts continuously with rich historical data (min/max)
- Dew point calculation done on-device

## References

- [BlueMaestro Advertisement Format](https://bluemaestro.com/interpret-bluetooth-advertisement-packet/) — Official protocol documentation
