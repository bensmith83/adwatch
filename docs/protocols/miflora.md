# Xiaomi MiFlora / Flower Care (Plant Sensor)

## Overview

The Xiaomi MiFlora (HHCCJCY01) is an extremely popular BLE plant sensor broadcasting soil moisture, temperature, light, and conductivity. Uses the MiBeacon protocol (service UUID `0xFE95`) — may already be partially handled by the existing `mibeacon` plugin, but MiFlora has specific device type IDs and data object formats worth explicit support.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE95` | Xiaomi MiBeacon protocol |
| Local name | `Flower care` or `Flower mate` | HHCCJCY01 |
| Device type | `0x0098` | MiFlora in MiBeacon frame |

### MiBeacon Frame (within service data for `0xFE95`)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0-1 | 2 | Frame control | Flags: encryption, MAC, capability, object |
| 2-3 | 2 | Device type | `0x0098` = MiFlora |
| 4 | 1 | Frame counter | Sequence number |
| 5-10 | 6 | MAC address | Optional (if flag set) |
| 11+ | var | Object data | Type-length-value sensor readings |

### MiFlora Object Types

| Object ID | Size | Field | Encoding |
|-----------|------|-------|----------|
| `0x1004` | 2 | Temperature | int16 LE, ÷ 10 = °C |
| `0x1007` | 3 | Illuminance | uint24 LE, lux |
| `0x1008` | 1 | Soil moisture | uint8, percent |
| `0x1009` | 2 | Conductivity | uint16 LE, µS/cm |
| `0x100A` | 1 | Battery | uint8, percent |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Temperature | object `0x1004` | °C with 0.1° resolution |
| Light level | object `0x1007` | Lux |
| Soil moisture | object `0x1008` | Percentage |
| Conductivity | object `0x1009` | µS/cm (soil fertility) |
| Battery | object `0x100A` | Percentage |

## Plugin Implementation Notes

- The existing `mibeacon` plugin may already catch these — check if device_type `0x0098` is recognized
- If mibeacon handles it generically, a dedicated MiFlora plugin may not be needed
- MiFlora broadcasts one object per advertisement (rotates through sensors)
- No encryption on HHCCJCY01 — data is in the clear
- Newer Tuya-based HHCCJCY10 uses a different protocol

## References

- **ESPHome docs**: https://esphome.io/components/sensor/xiaomi_ble/
- **Protocol wiki**: https://github.com/ChrisScheffler/miflora/wiki/The-Basics
- **MiBeacon protocol**: https://home-is-where-you-hang-your-hack.github.io/ble_monitor/MiBeacon_protocol
