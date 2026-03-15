# EnOcean BLE Sensors — Energy-Harvesting

## Overview

EnOcean produces self-powered (energy-harvesting) BLE sensors for commercial building automation. Sensors harvest energy from light, motion, or temperature differentials — no batteries required. They broadcast sensor data with optional AES-128 CMAC authentication.

## Identification

- **Company ID:** `0x03DA` (EnOcean GmbH)

## Advertisement Format

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Company ID | uint16 LE (`0x03DA`) |
| 2 | 1 | Sequence counter | uint8 — increments per telegram (replay detection) |
| 3 | 1 | Switch/event type | uint8 — identifies the event or sensor module |
| 4+ | var | Sensor data | Format depends on sensor module type |
| last 4 | 4 | Security signature | AES-128 CMAC (optional, for authenticated telegrams) |

### Sensor Module: STM550B (Multi-Sensor)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 4-5 | 2 | Temperature | int16 LE / 100 = degrees C |
| 6 | 1 | Humidity | uint8 = % RH |
| 7-8 | 2 | Illumination | uint16 LE = lux |
| 9-10 | 2 | Accel X | int16 LE — milli-g |
| 11-12 | 2 | Accel Y | int16 LE |
| 13-14 | 2 | Accel Z | int16 LE |
| 15 | 1 | Magnet contact | `0`=open, `1`=closed |

### Sensor Module: EMDCB (Motion Detector)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 4 | 1 | Motion | `0`=no motion, `1`=motion detected |
| 5-6 | 2 | Illumination | uint16 LE = lux |

### Sensor Module: PTM 216B (Pushbutton)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 4 | 1 | Button event | Bits: rocker A/B, press/release, energy status |

## Security

Authenticated telegrams include a 4-byte AES-128 CMAC signature at the end of the payload. The sequence counter prevents replay attacks. Validation requires the per-device AES key (provisioned during commissioning).

For passive monitoring without authentication validation, the sensor data can still be extracted — just skip the last 4 bytes.

## ParseResult Fields

- `sensor_module` (str): "stm550b", "emdcb", "ptm216b", "unknown"
- `sequence` (int): Telegram sequence counter
- `temperature` (float): Temperature in C (STM550B)
- `humidity` (int): Humidity % (STM550B)
- `illumination` (int): Illuminance in lux (STM550B, EMDCB)
- `accel_x`, `accel_y`, `accel_z` (int): Acceleration in milli-g (STM550B)
- `magnet_contact` (bool): Magnet contact state (STM550B)
- `motion` (bool): Motion detected (EMDCB)
- `button_event` (str): Button press description (PTM 216B)
- `authenticated` (bool): Whether security signature is present

## References

- https://www.enocean.com/en/products/enocean_modules_24ghz_ble/
- https://github.com/futomi/node-enocean-ble
