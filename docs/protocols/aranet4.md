# Aranet4 (CO2 Monitor)

## Overview

Aranet4 is a popular standalone CO2 monitor used for indoor air quality assessment. It broadcasts environmental readings passively via BLE manufacturer data, making it ideal for passive monitoring without GATT connections.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `f0cd3001-95da-4f4b-9ac8-aa55d312af0c` | Aranet custom UUID |
| Local name | `Aranet4 XXXXX` | Device name with serial suffix |

### Advertisement Payload (13 bytes)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-1 | CO2 | uint16 LE | Raw value | ppm |
| 2-3 | Temperature | uint16 LE | `value / 20` | °C |
| 4-5 | Atmospheric pressure | uint16 LE | `value / 10` | hPa |
| 6 | Humidity | uint8 | Raw value | % |
| 7 | Battery | uint8 | Raw value | % |
| 8 | Status/color | uint8 | 0=green, 1=yellow, 2=red | — |
| 9-10 | Measurement interval | uint16 LE | Raw value | seconds |
| 11-12 | Time since update | uint16 LE | Time since last reading | seconds |

### CO2 Status Thresholds

| Status | Color | CO2 Range | Meaning |
|--------|-------|-----------|---------|
| 0 | Green | < 1000 ppm | Good air quality |
| 1 | Yellow | 1000-1400 ppm | Moderate, ventilate soon |
| 2 | Red | > 1400 ppm | Poor, ventilate immediately |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| CO2 | payload[0:2] | Parts per million |
| Temperature | payload[2:4] | Celsius, /20 |
| Pressure | payload[4:6] | Hectopascals, /10 |
| Humidity | payload[6] | Percentage |
| Battery | payload[7] | Percentage |
| Air quality status | payload[8] | Green/yellow/red enum |
| Measurement interval | payload[9:11] | How often sensor updates |
| Data age | payload[11:13] | Freshness of the reading |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Indicates indoor air quality monitoring (post-COVID awareness)
- CO2 readings are valuable environmental data
- Common in offices, schools, and health-conscious homes
- Broadcasts at configurable intervals (default 60 seconds)

## References

- [Theengs Aranet4](https://decoder.theengs.io/devices/Aranet4.html) — Theengs decoder documentation
- [esphome-aranet4](https://github.com/stefanthoss/esphome-aranet4) — ESPHome component
- [Aranet4-Python](https://github.com/Anrijs/Aranet4-Python) — Official Python library
