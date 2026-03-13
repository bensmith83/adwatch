# iBBQ / Inkbird BBQ Thermometer

## Overview

iBBQ is a family of wireless BBQ probe thermometers by Inkbird (IBT-2X, IBT-4XS, IBT-6XS, IBBQ-4T, IBBQ-4BW). They broadcast probe temperatures passively in manufacturer-specific data — no GATT connection needed for basic temperature readings.

**Note:** These are distinct from Inkbird's IBS-TH environmental sensors (already handled by the `inkbird` plugin). iBBQ devices use local name `iBBQ` and service UUID `0xFFF0`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `iBBQ` | Exact match |
| Service UUID | `0xFFF0` | 16-bit, in Complete Service UUID list |
| Company ID | `0x0000` | Too generic to use alone — combine with local name |

### Manufacturer Data Layout (variable length, little-endian)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-1 | Company ID | uint16 LE | `0x0000` | — |
| 2-3 | Reserved | 2 bytes | Usually `0x0000` | — |
| 4-5 | Reserved | 2 bytes | Usually `0x0000` | — |
| 6-11 | Device MAC | 6 bytes | Little-endian MAC address | — |
| 12-13 | Probe 1 temp | int16 LE | `value / 10.0` | °C |
| 14-15 | Probe 2 temp | int16 LE | `value / 10.0` | °C |
| 16-17 | Probe 3 temp | int16 LE | `value / 10.0` (4+ probe models) | °C |
| 18-19 | Probe 4 temp | int16 LE | `value / 10.0` (4+ probe models) | °C |
| 20-21 | Probe 5 temp | int16 LE | `value / 10.0` (6 probe models) | °C |
| 22-23 | Probe 6 temp | int16 LE | `value / 10.0` (6 probe models) | °C |

### Temperature Encoding

```python
temp_raw = int.from_bytes(data[offset:offset+2], 'little', signed=True)
temp_celsius = temp_raw / 10.0
```

Disconnected probe sentinel: `0xFFF6` (-10 raw = -1.0°C). Skip these values.

### Probe Count by Model

| Model | Probes | Manufacturer Data Length |
|-------|--------|------------------------|
| IBT-2X / IBT-2XS | 2 | ~16 bytes |
| IBT-4XS / IBBQ-4T / IBBQ-4BW | 4 | ~20 bytes |
| IBT-6XS | 6 | ~24 bytes |

The number of probes can be derived from the manufacturer data length: `(len - 12) / 2`.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Probe temperatures | mfr_data[12:] | All connected probes, °C |
| Number of probes | Derived from data length | 2, 4, or 6 |
| Active probes | Filter non-sentinel values | Skip 0xFFF6 |
| Device MAC | mfr_data[6:12] | Stable identifier |

### What Requires GATT Connection

- Battery level
- Historical temperature logs
- Target temperature alarms
- Temperature unit preference (°C/°F)

## Identity Hashing

```
identifier = SHA256("{mac}:iBBQ")[:16]
```

## Known Models

| Model | Probes | Notes |
|-------|--------|-------|
| IBT-2X | 2 | Basic dual-probe |
| IBT-2XS | 2 | Updated version |
| IBT-4XS | 4 | Most popular model |
| IBBQ-4T | 4 | WiFi + BLE variant |
| IBBQ-4BW | 4 | WiFi + BLE variant |
| IBT-6XS | 6 | Six-probe model |

## Detection Significance

- Very common BBQ/grilling accessory
- Broadcasts continuously when powered on
- Real probe temperatures available passively — high-value data
- Complements existing thermopro/inkbird plugins
- Multiple probes per device = rich telemetry

## References

- [iBBQ Protocol Gist](https://gist.github.com/uucidl/b9c60b6d36d8080d085a8e3310621d64) — Primary protocol reference
- [ble_monitor #585](https://github.com/custom-components/ble_monitor/issues/585) — Raw advertisement captures
- [Theengs Decoder — IBT-2X](https://decoder.theengs.io/devices/IBT_2X.html)
- [Theengs Decoder — IBT-4XS](https://decoder.theengs.io/devices/IBT_4XS.html)
- [inkbird-ble](https://github.com/Bluetooth-Devices/inkbird-ble) — Home Assistant parser
- [Adafruit CircuitPython BLE iBBQ](https://github.com/adafruit/Adafruit_CircuitPython_BLE_iBBQ) — GATT docs
