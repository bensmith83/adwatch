# Kegtron (Beer Keg Monitor)

## Overview

Kegtron is a beer keg monitoring system that tracks remaining volume via a BLE flow meter. The manufacturer officially documents their BLE protocol and encourages DIY integration via their "Hack Your Taps" page.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xFFFF` | Generic/unassigned (requires local name check) |
| Local name | `Kegtron`, `KT-` prefix | Identifies as Kegtron device |

### Manufacturer Data Layout (31-byte scan response)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-1 | Company ID | uint16 LE | `0xFFFF` | — |
| 2 | Port index | uint8 | 0 = single/port A, 1 = port B | — |
| 3-4 | Keg size | uint16 LE | Raw value | mL |
| 5-6 | Volume start | uint16 LE | Initial volume | mL |
| 7-8 | Volume dispensed | uint16 LE | Total poured | mL |
| 9+ | Port name | UTF-8 | Null-terminated string | — |

### Derived Values

```python
volume_remaining = volume_start - volume_dispensed
percent_remaining = volume_remaining / keg_size * 100
```

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Keg size | mfr_data[3:5] | Total keg capacity in mL |
| Volume start | mfr_data[5:7] | Starting fill level in mL |
| Volume dispensed | mfr_data[7:9] | Total poured in mL |
| Volume remaining | Derived | start - dispensed |
| Percent remaining | Derived | remaining / size × 100 |
| Port/tap name | mfr_data[9:] | User-assigned tap name |
| Dual-tap port | mfr_data[2] | Which tap (0=A, 1=B) |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Niche but fun — indicates a kegerator/draft system nearby
- Dual-tap models advertise two separate readings
- Volume tracking is useful telemetry data
- Officially documented protocol (manufacturer encourages integration)

## References

- [Kegtron Hack Your Taps](https://kegtron.com/hack-your-taps/) — Official integration page
