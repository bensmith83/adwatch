# ATC/PVVX Custom Firmware Thermometers

## Overview

ATC and PVVX are popular custom firmware projects for cheap Xiaomi LYWSD03MMC (and similar) BLE thermometers. When configured in "custom" or "ATC1.1" mode (as opposed to BTHome mode), these devices broadcast in a distinct format on service UUID `0x181A`. This is separate from BTHome (UUID `0xFCD2`) which adwatch already parses.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x181A` | ATC custom format (NOT BTHome) |
| Local name | `ATC_XXXXXX`, `LYWSD03MMC` | Varies by firmware config |

### ATC1.1 Custom Format — Service Data on UUID 0x181A (13-15 bytes)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-5 | MAC address | 6 bytes | Device MAC | — |
| 6-7 | Temperature | int16 BE | `value / 100` (signed) | °C |
| 8-9 | Humidity | uint16 BE | `value / 100` | % |
| 10-11 | Battery voltage | uint16 BE | Raw value | mV |
| 12 | Battery level | uint8 | Raw value | % |
| 13 | Frame counter | uint8 | Incrementing counter | — |
| 14 | Flags | uint8 | See flags table | — |

**Note:** ATC format uses **big-endian** byte order, unlike most BLE protocols.

### PVVX Extended Format — Service Data on UUID 0x181A (18 bytes)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-5 | MAC address | 6 bytes | Device MAC | — |
| 6-7 | Temperature | int16 LE | `value / 100` (signed) | °C |
| 8-9 | Humidity | uint16 LE | `value / 100` | % |
| 10-11 | Battery voltage | uint16 LE | Raw value | mV |
| 12 | Battery level | uint8 | Raw value | % |
| 13 | Frame counter | uint8 | Incrementing | — |
| 14 | Flags | uint8 | See flags table | — |
| 15 | Reserved | uint8 | — | — |
| 16-17 | Trigger data | 2 bytes | Event triggers | — |

**Note:** PVVX extended format uses **little-endian** byte order.

### Flags Byte

| Bit | Meaning |
|-----|---------|
| 0 | Temperature trigger |
| 1 | Humidity trigger |
| 2-3 | Trigger type |
| 4 | Comfort indicator |

### Format Detection

Distinguish ATC vs PVVX by service data length:
- 13-15 bytes → ATC1.1 format (big-endian)
- 18 bytes → PVVX extended format (little-endian)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Temperature | service_data[6:8] | °C, /100, signed |
| Humidity | service_data[8:10] | %, /100 |
| Battery voltage | service_data[10:12] | Millivolts |
| Battery level | service_data[12] | Percentage |
| Frame counter | service_data[13] | For dedup/ordering |
| Format | Data length | ATC vs PVVX detection |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

The MAC embedded in service data is stable and matches the advertising MAC (these devices don't randomize).

## Detection Significance

- Very common in the home automation community
- Indicates a user running custom firmware (tech-savvy household)
- Cheap sensors (~$5 each), often deployed in multiples
- Broadcasts every few seconds with fresh readings

## References

- [pvvx/ATC_MiThermometer](https://github.com/pvvx/ATC_MiThermometer) — Firmware source + protocol documentation
- [ATC custom format README](https://github.com/pvvx/ATC_MiThermometer/blob/master/README.md#custom-format-all-data-little-endian) — Format specification
