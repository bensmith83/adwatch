# ELA Innovation — Industrial BLE Sensors

## Overview

ELA Innovation (France) produces industrial BLE sensors with EN12830 certification for cold chain monitoring. Models include Blue PUCK T (temperature), Blue PUCK RHT (temp + humidity), Blue COIN T (compact temp).

## Identification

- **Company ID:** `0x0757` (ELA Innovation)

## Advertisement Format

Two firmware generations with different formats:

### Firmware >= 2.0 (Manufacturer-Specific Data)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-1 | 2 | Company ID | uint16 LE (`0x0757`) |
| 2 | 1 | Frame type | uint8 — `0x01`=sensor data, `0x02`=device info |
| 3 | 1 | Frame counter | uint8 — increments per advertisement |

#### Sensor Data Frame (type `0x01`)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 4-5 | 2 | Temperature | int16 LE / 100 = degrees C (signed) |
| 6-7 | 2 | Humidity | uint16 LE / 100 = % (RHT models only) |
| 8 | 1 | Battery | uint8 = % |

#### Device Info Frame (type `0x02`)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 4-5 | 2 | Firmware version | uint16 BE — major.minor |
| 6-7 | 2 | Hardware version | uint16 BE |
| 8 | 1 | Sensor model | uint8 — model identifier |

### Firmware < 2.0 (Service Data)

Older firmware uses service data advertisements. Format is similar but encapsulated in service data rather than manufacturer data.

## ParseResult Fields

- `temperature` (float): Temperature in degrees C
- `humidity` (float): Humidity in % (RHT models only, None otherwise)
- `battery` (int): Battery percentage
- `frame_counter` (int): Advertisement counter
- `firmware_version` (str): Firmware version (info frame only)
- `model` (str): Sensor model name (info frame only)

## References

- https://elainnovation.com/wp-content/uploads/2020/10/BLE-Frame-specifications-11B-EN.pdf
