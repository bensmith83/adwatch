# SmartDry — Laundry Sensor

## Overview

SmartDry is a sensor placed in the dryer drum to detect when laundry is done by monitoring temperature and humidity inside the dryer. The cloud service was shut down in 2022, making local BLE parsing the only way to use these devices.

## Identification

- **Company ID:** `0x01AE`

## Advertisement Format

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Company ID | uint16 LE (`0x01AE`) |
| 2-3 | 2 | Temperature | int16 LE / 100 = degrees C (inside dryer) |
| 4-5 | 2 | Humidity | uint16 LE / 100 = % (inside dryer) |
| 6 | 1 | Battery | uint8 = % |
| 7 | 1 | Shake intensity | uint8 — tumble/rotation activity level |

## Dryer State Inference

The shake intensity and temperature together indicate dryer state:

- **Idle:** Low temperature, zero shake
- **Running:** High temperature, high shake intensity
- **Done:** Temperature dropping, shake stopped
- **Cool-down:** Temperature dropping, shake still present (some dryers)

## ParseResult Fields

- `temperature` (float): Temperature inside dryer (C)
- `humidity` (float): Humidity inside dryer (%)
- `battery` (int): Battery percentage
- `shake_intensity` (int): Tumble activity level (0-255)

## References

- https://decoder.theengs.io/devices/SDLS.html
