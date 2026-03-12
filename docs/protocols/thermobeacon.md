# ThermoBeacon (Brifit/Oria/Thermoplus)

## Overview

ThermoBeacon is a family of cheap BLE temperature/humidity sensors sold under many Amazon brands (Brifit, Oria, Thermoplus, Lanyard, etc.). They broadcast environmental data passively in manufacturer-specific data without requiring a GATT connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0011` | ThermoBeacon manufacturer |
| Local name | `TP3xx`, `Lanyard` | Varies by reseller brand |

### Manufacturer Data Layout (18-20 bytes, little-endian)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-5 | Device MAC | 6 bytes | Reversed byte order | — |
| 6-7 | Temperature | int16 LE | `value / 16` (if > 4000, subtract 4096) | °C |
| 8-9 | Humidity | uint16 LE | `value / 16` | % |
| 10-11 | Battery voltage | uint16 LE | Raw millivolts | mV |
| 12-17 | Uptime/counter | 6 bytes | Varies by model | — |

### Temperature Encoding Quirk

Temperature uses divide-by-16 with a wraparound for negative values:
```python
temp_raw = int.from_bytes(data[6:8], 'little', signed=False)
if temp_raw > 4000:
    temp_raw -= 4096
temperature = temp_raw / 16.0
```

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Temperature | mfr_data[6:8] | °C, signed, /16 |
| Humidity | mfr_data[8:10] | %, /16 |
| Battery voltage | mfr_data[10:12] | millivolts |
| Device MAC | mfr_data[0:6] | Reversed, stable identifier |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

The MAC embedded in the manufacturer data is stable and can supplement the BLE MAC for identity.

## Known Brands/Models

| Brand | Model Pattern | Notes |
|-------|--------------|-------|
| Brifit | TP357, TP358 | Most common on Amazon |
| Oria | TP3xx | Same hardware, different branding |
| Thermoplus | TP3xx | Same hardware |
| Generic | "Lanyard" | Wearable variant |

## Detection Significance

- Very common in homes (cheap Amazon sensors)
- Broadcasts continuously (~1-2 second intervals)
- Useful for ambient environment monitoring
- Multiple sensors per household is typical

## References

- [thermobeacon-ble](https://github.com/Bluetooth-Devices/thermobeacon-ble) — Python parser
- [Theengs ThermoBeacon](https://decoder.theengs.io/devices/ThermoBeacon.html) — Theengs decoder docs
- [rnlgreen/thermobeacon](https://github.com/rnlgreen/thermobeacon) — Protocol analysis
