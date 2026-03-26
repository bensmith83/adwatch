# b-parasite (Open Source Soil Sensor)

## Overview

b-parasite is an open-source BLE soil moisture, temperature, humidity, and light sensor. It broadcasts all sensor data passively via BLE advertisements — no connection required. The firmware supports three encoding formats; the custom v2 format is most distinctive.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x181A` | Environmental Sensing (v2 custom format) |
| Service UUID | `0xFCD2` | BTHome v2 (default in newer firmware) |
| Local name | `prst` | Default device name (user-configurable) |

### v2 Custom Protocol — Service Data Layout (UUID `0x181A`)

Service data is 20 bytes (including the 2-byte UUID):

| Offset | Size | Field | Encoding | Notes |
|--------|------|-------|----------|-------|
| 0-1 | 2 | Service UUID | `0x1A 0x18` (LE) | Environmental Sensing |
| 2 | 1 | Protocol + flags | Upper nibble: version (`0x2_` = v2). Bit 0: has light data | |
| 3 | 1 | Counter | Lower nibble: 4-bit wrap-around dedup counter | |
| 4-5 | 2 | Battery voltage | uint16 BE, millivolts | e.g. `0x0BE0` = 3040 mV |
| 6-7 | 2 | Temperature | int16 BE, centi-celsius (÷ 100 = °C) | e.g. `0x09C4` = 25.00°C |
| 8-9 | 2 | Humidity | uint16 BE, 0–65535 → 0–100% | value / 65535 × 100 |
| 10-11 | 2 | Soil moisture | uint16 BE, 0–65535 → 0–100% | value / 65535 × 100 |
| 12-17 | 6 | MAC address | Big-endian | |
| 18-19 | 2 | Illuminance | uint16 BE, raw brightness | Only valid if bit 0 of byte 2 is set |

### BTHome v2 Format (UUID `0xFCD2`)

Uses standard BTHome self-describing format — would be handled by existing `bthome` plugin. Objects broadcast: battery %, temperature, illuminance, voltage, humidity, soil moisture.

## Plugin Implementation Notes

- Match on service UUID `0x181A` with protocol version nibble `0x2_` at byte 2
- Alternatively match on local name `prst`
- BTHome v2 encoded devices are already handled by the existing `bthome` plugin
- Advertising interval: wakes every ~600s, advertises for 1s at 30–40ms intervals

## Identity Hashing

```
identifier = SHA256("{mac}:{battery_voltage}:{soil_moisture}")[:16]
```

Or simpler: use MAC-based identity since each sensor has a unique MAC.

## References

- **Firmware source**: https://github.com/rbaron/b-parasite
- **Protocol encoding**: `code/nrf-connect/samples/ble/src/encoding.c`
- **Theengs decoder**: https://decoder.theengs.io/devices/b-parasite.html
