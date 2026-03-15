# Smart Sensor Devices — Environmental Sensors

## Overview

Smart Sensor Devices AB (Sweden) produces BlueBerry series industrial environmental sensors. They broadcast sensor readings via BLE manufacturer-specific data.

## Identification

- **Company ID:** `0x075B` (Smart Sensor Devices AB)

## Advertisement Format

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Company ID | uint16 LE (`0x075B`) |
| 2 | 1 | Sensor type | uint8 — identifies which sensor readings follow |
| 3-4 | 2 | Primary value | int16 LE — scaled per sensor type |
| 5 | 1 | Battery | uint8 = % |

### Sensor Types

| Type | Name | Primary Value Scaling |
|------|------|-----------------------|
| `0x01` | Temperature | / 100 = degrees C |
| `0x02` | Humidity | / 100 = % |
| `0x03` | Pressure | / 10 = hPa |
| `0x04` | Light | = lux |
| `0x05` | Air quality | = IAQ index |

## ParseResult Fields

- `sensor_type` (str): "temperature", "humidity", "pressure", "light", "air_quality"
- `value` (float): Primary sensor reading (units depend on type)
- `battery` (int): Battery percentage

## References

- https://github.com/reelyactive/advlib-ble-manufacturers
