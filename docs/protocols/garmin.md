# Garmin Wearable Plugin

## Overview

Garmin is one of the most popular wearable/fitness device manufacturers. Their watches and fitness trackers (Forerunner, Fenix, Venu, Vivoactive, Lily, Instinct) advertise over BLE for phone connectivity and sensor broadcasting. Garmin watches are extremely common — nearly every runner/cyclist in a neighborhood has one.

## Supported Device Families

| Family | Example Models | Local Name Pattern |
|--------|---------------|-------------------|
| Forerunner | 55, 165, 255, 265, 745, 945, 965 | `Forerunner *` or `FR*` |
| Fenix | 6, 7, 8 | `fenix *` |
| Venu | Venu, Venu 2, Venu 3, Venu Sq | `Venu*` |
| Vivoactive | 4, 5 | `vivoactive*` or `VA*` |
| Instinct | 1, 2, 3, Crossover | `Instinct*` |
| Lily | 1, 2 | `Lily*` |
| Vivosmart | 4, 5 | `vivosmart*` |
| Edge | 530, 540, 830, 840, 1040, 1050 | `Edge *` |
| HRM | HRM-Pro, HRM-Dual | `HRM-*` |
| Index | Index S2 (smart scale) | `Index*` |
| Vivomove | Trend, Style | `vivomove*` |

## BLE Advertisement Format

### Identification

Garmin devices can be identified by:

1. **Company ID**: `0x0087` (Garmin International, Inc. — decimal 135)
2. **Local Name Pattern**: Model family names listed above
3. **Service UUID**: May advertise standard GATT services like Heart Rate (`0x180D`)

Best match strategy: `company_id=0x0087` (catches all Garmin devices regardless of name).

### Manufacturer Data (Company ID 0x0087)

```
Offset  Length  Field            Description
0       2       Company ID       0x8700 (LE) = 0x0087
2       1       Message Type     Advertisement type identifier
3       var     Payload          Type-specific data
```

The manufacturer data format varies by device and message type. Common patterns:
- Byte 2 often indicates connection state or advertising mode
- Remaining bytes contain device-specific identifiers

### Common Service UUIDs

Garmin devices may advertise these standard BLE services:
- `0x180D` — Heart Rate (HRM straps)
- `0x1816` — Cycling Speed and Cadence (Edge devices)
- `0x1818` — Cycling Power
- `0x180F` — Battery Service
- `6A4E####-667B-11E3-949A-0800200C9A66` — Garmin proprietary service base

### Parser Strategy

- Register with `company_id=0x0087`
- Extract device family/model from local_name if available
- Parse manufacturer data for device type and state
- Identify HRM vs watch vs cycling computer from service UUIDs
- Return ParseResult with device_type, model_family, and any extractable state

## References

- [Garmin Connect IQ SDK](https://developer.garmin.com/connect-iq/)
- [Bluetooth SIG Company ID 0x0087](https://www.bluetooth.com/specifications/assigned-numbers/)
- [ANT+ / BLE Garmin Sensors](https://www.thisisant.com/developer/ant-plus/ant-plus-basics/)
- [nRF Connect profiles for Garmin devices](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)
