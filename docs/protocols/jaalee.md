# Jaalee BLE Sensors — Temperature/Humidity Beacon

## Overview

Jaalee produces budget BLE temperature/humidity beacons (models F525, F51C, etc.) that broadcast sensor data via service data on a custom UUID.

## Identification

- **Service UUID:** `0x9717` (service data key)

## Advertisement Format

Service data with UUID16 `0x9717`:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Service UUID | `0x9717` (already consumed as key) |
| 2-3 | 2 | Temperature | int16 LE / 100 = degrees C (signed) |
| 4-5 | 2 | Humidity | uint16 LE / 100 = % |
| 6 | 1 | Battery | uint8 = % |

## ParseResult Fields

- `temperature` (float): Temperature in degrees C
- `humidity` (float): Humidity in %
- `battery` (int): Battery percentage

## References

- https://decoder.theengs.io/
