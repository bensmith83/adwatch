# Minew Sensors — Industrial BLE Beacons

## Overview

Minew Technologies produces industrial BLE beacons and sensors (S1 temp/humidity, S4 accelerometer, various beacon models). They use multi-slot advertising with up to 10 concurrent frames, mixing iBeacon, Eddystone, and custom sensor data frames.

## Identification

- **Company ID:** `0x0639` (Minew Technologies)

## Advertisement Format

Manufacturer-specific data with frame type selector:

### Frame Types

| Frame Type | Name | Description |
|-----------|------|-------------|
| `0xA1` | Info frame | Device information, battery, MAC |
| `0xA2` | Sensor frame | Temperature and humidity readings |
| `0xA3` | Accel frame | Accelerometer X/Y/Z values |

### Info Frame (`0xA1`)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Frame type | `0xA1` |
| 1 | 1 | Product model | uint8 — model identifier |
| 2-7 | 6 | MAC address | 6 bytes, big-endian |
| 8 | 1 | Battery | uint8 — percentage (0-100) |
| 9-10 | 2 | Firmware ver | uint16 BE — major.minor |

### Sensor Frame (`0xA2`)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Frame type | `0xA2` |
| 1-2 | 2 | Temperature | int16 BE / 256.0 = degrees C |
| 3-4 | 2 | Humidity | uint16 BE / 256.0 = % |

### Accelerometer Frame (`0xA3`)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Frame type | `0xA3` |
| 1-2 | 2 | Accel X | int16 BE — milli-g |
| 3-4 | 2 | Accel Y | int16 BE — milli-g |
| 5-6 | 2 | Accel Z | int16 BE — milli-g |

## ParseResult Fields

- `frame_type` (str): "info", "sensor", "accelerometer"
- `temperature` (float): Temperature in C (sensor frame)
- `humidity` (float): Humidity in % (sensor frame)
- `battery` (int): Battery percentage (info frame)
- `accel_x`, `accel_y`, `accel_z` (int): Acceleration in milli-g (accel frame)
- `mac` (str): Device MAC address (info frame)
- `firmware_version` (str): Firmware version string (info frame)

## References

- https://github.com/reelyactive/advlib-ble-manufacturers
- https://reelyactive.github.io/diy/minew-s1-config/
