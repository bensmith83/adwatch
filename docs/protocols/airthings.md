# Airthings Wave (Air Quality Monitor)

## Overview

Airthings makes popular indoor air quality monitors (radon, CO2, VOC, humidity, temperature). Devices broadcast a serial number and model identification in BLE advertisements. Sensor readings require a GATT connection — this parser provides device detection and classification.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0334` (820) | Airthings AS |
| Local name | `AT#NNNNNN-2900Radon` | Wave Gen 1 only; other models may not have distinctive names |

### Manufacturer Data Layout (minimum 4 bytes after company ID)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-3 | Serial Number | uint32 LE | 10-digit serial on device label | — |

### Model Identification from Serial Number Prefix

The first 4 digits of the serial number identify the model:

| Prefix | Model | Product Name |
|--------|-------|-------------|
| `2900` | WAVE_GEN_1 | Wave Gen 1 (radon) |
| `2920` | WAVE_MINI | Wave Mini (VOC, temp, humidity) |
| `2930` | WAVE_PLUS | Wave Plus (radon, CO2, VOC, temp, humidity, pressure) |
| `2950` | WAVE_RADON | Wave Radon Gen 2 |
| `3210` | WAVE_ENHANCE_EU | Wave Enhance (EU) |
| `3220` | WAVE_ENHANCE_US | Wave Enhance (US) |
| `3250` | CORENTIUM_HOME_2 | Corentium Home 2 |

### Service UUIDs (advertised, model-specific)

| Model | Service UUID |
|-------|-------------|
| Wave Plus | `b42e1c08-ade7-11e4-89d3-123b93f75cba` |
| Wave Mini | `b42e3882-ade7-11e4-89d3-123b93f75cba` |
| Wave Radon Gen 2 | `b42e4a8e-ade7-11e4-89d3-123b93f75cba` |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Serial number | mfr_data[0:4] | uint32 LE, matches label on device |
| Model | Derived from serial prefix | 7 known models |
| Model (alt) | Service UUID | If advertised |

### What Requires GATT Connection

- Radon level (Bq/m³)
- CO2 (ppm)
- VOC (ppb)
- Temperature (°C)
- Humidity (%)
- Atmospheric pressure (hPa)
- Ambient light
- Battery level

## Identity Hashing

```
identifier = SHA256("{mac}:{serial_number}")[:16]
```

## Detection Significance

- Very popular post-COVID for indoor air quality monitoring
- Presence detection identifies households with air quality concerns
- Serial number allows tracking specific devices
- Model identification reveals sensor capabilities (radon, CO2, etc.)

## References

- [airthings-ble](https://github.com/Airthings/airthings-ble) — Official Python library
- [ESPHome Airthings BLE](https://esphome.io/components/sensor/airthings_ble/) — Passive listener reference
- [wave-reader](https://github.com/Airthings/wave-reader) — Official Wave reader
- [waveplus-reader](https://github.com/Airthings/waveplus-reader) — Official Wave Plus reader
