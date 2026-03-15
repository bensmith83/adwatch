# Teltonika EYE Sensor — Industrial Multi-Sensor

## Overview

Teltonika EYE Sensor (BTSMP1) and EYE Beacon (BTSID1) are industrial-grade BLE sensors broadcasting environmental and motion data. Used for fleet management, asset tracking, and condition monitoring.

## Identification

- **Company ID:** `0x089A` (Teltonika)

## Advertisement Format

Manufacturer-specific data in scan response:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Company ID | uint16 LE (`0x089A`) |
| 2 | 1 | Protocol version | uint8 (`0x01`) |
| 3 | 1 | Flags | Bitfield — indicates which sensor fields follow |
| 4+ | var | Sensor data | Only present fields included, in flag-bit order |

### Flags Bitfield (byte 3)

| Bit | Field | Size if present | Encoding |
|-----|-------|----------------|----------|
| 0 | Temperature | 2 bytes | int16 LE / 100 = degrees C |
| 1 | Humidity | 1 byte | uint8 = % RH |
| 2 | Magnetic field | 1 byte | `0`=no magnet, `1`=magnet detected |
| 3 | Movement counter | 2 bytes | uint16 LE — increments on each detected movement |
| 4 | Pitch angle | 2 bytes | int16 LE = degrees (-90 to +90) |
| 5 | Roll angle | 2 bytes | int16 LE = degrees (-180 to +180) |
| 6 | Battery voltage | 2 bytes | raw value: `(2000 + value * 10)` mV |

### Variable-Length Parsing

Fields appear in the payload **only if their flag bit is set**, in bit order (bit 0 first). To parse:

```python
offset = 4
if flags & 0x01:
    temp = int.from_bytes(data[offset:offset+2], 'little', signed=True) / 100
    offset += 2
if flags & 0x02:
    humidity = data[offset]
    offset += 1
if flags & 0x04:
    magnet = bool(data[offset])
    offset += 1
# ... etc
```

## ParseResult Fields

- `temperature` (float): Temperature in degrees C
- `humidity` (int): Relative humidity %
- `magnet_detected` (bool): Magnetic field presence
- `movement_count` (int): Cumulative movement counter
- `pitch` (float): Pitch angle in degrees
- `roll` (float): Roll angle in degrees
- `battery_mv` (int): Battery voltage in millivolts

## References

- https://wiki.teltonika-gps.com/view/EYE_SENSOR_/_BTSMP1
