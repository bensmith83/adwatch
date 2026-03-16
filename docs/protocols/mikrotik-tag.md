# MikroTik BLE Tag — Asset Tracking

## Overview

MikroTik TG-BT5-IN (indoor) and TG-BT5-OUT (outdoor) are asset tracking BLE tags. They support three advertisement modes: iBeacon, Eddystone, and a custom MikroTik format with sensor data. This parser targets the custom format.

## Identification

- **Manufacturer data:** MikroTik-specific prefix bytes when in custom format mode
- **Note:** When configured as iBeacon or Eddystone, those existing parsers will handle them

## Advertisement Format (Custom MikroTik)

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Version | uint8 — protocol version |
| 1 | 1 | Flags | Bitfield: bit 0 = encrypted, bit 1 = salt present, bit 2 = MAC included |
| 2-7 | 6 | MAC address | 6 bytes (if flags bit 2 set, otherwise omitted) |
| next | 2 | Accel X | int16 LE — acceleration in milli-g |
| next | 2 | Accel Y | int16 LE — acceleration in milli-g |
| next | 2 | Accel Z | int16 LE — acceleration in milli-g |
| next | 2 | Temperature | int16 LE / 256 = degrees C |
| next | 2 | Uptime | uint16 LE — seconds since boot |
| next | 1 | Battery | uint8 — percentage (0-100) |

### Encrypted Mode

When flags bit 0 is set, sensor data payload is AES-128 encrypted. A 4-byte salt is prepended (if flags bit 1 set) used as part of the nonce for decryption.

## Derived Values

```python
# Tilt angle from accelerometer
import math
tilt = math.degrees(math.atan2(
    math.sqrt(accel_x**2 + accel_y**2), accel_z
))
```

## ParseResult Fields

- `accel_x` (int): X-axis acceleration (milli-g)
- `accel_y` (int): Y-axis acceleration (milli-g)
- `accel_z` (int): Z-axis acceleration (milli-g)
- `tilt_angle` (float): Derived tilt angle (degrees)
- `temperature` (float): Temperature (C)
- `uptime` (int): Seconds since boot
- `battery` (int): Battery percentage
- `encrypted` (bool): Whether payload is encrypted

## References

- https://help.mikrotik.com/docs/spaces/UM/pages/105742533/MikroTik+Tag+advertisement+formats
