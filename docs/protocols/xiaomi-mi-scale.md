# Xiaomi Mi Scale

## Overview

Xiaomi Mi Smart Scale (v1) and Mi Body Composition Scale (v2) broadcast weight measurements passively via standard BLE service data. No GATT connection is needed — the scale advertises the measurement result after a reading stabilizes.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x181D` | Mi Scale v1 (Weight Scale service) |
| Service UUID | `0x181B` | Mi Scale v2 / Body Composition Scale |
| Local name | `MIBFS`, `XMTZC01HM`, `XMTZC02HM`, `XMTZC04HM`, `XMTZC05HM` | Varies by model |

### Mi Scale v1 — Service Data on UUID 0x181D (10 bytes)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-1 | Control flags | uint16 LE | See flags table below | — |
| 2-3 | Year | uint16 LE | Calendar year | — |
| 4 | Month | uint8 | 1-12 | — |
| 5 | Day | uint8 | 1-31 | — |
| 6 | Hour | uint8 | 0-23 | — |
| 7 | Minute | uint8 | 0-59 | — |
| 8 | Second | uint8 | 0-59 | — |
| 9-10 | Weight | uint16 LE | `/200` for kg, `/100` for lbs/jin | kg/lbs |

### Mi Scale v2 — Service Data on UUID 0x181B (13 bytes)

Same as v1, plus:

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 11-12 | Impedance | uint16 LE | Raw value for body composition calc | Ω |

### Control Flags (bytes 0-1 as uint16 LE)

| Bit | Meaning |
|-----|---------|
| 0 | Unit: 0 = kg, 1 = lbs |
| 4 | Stabilized (measurement complete) |
| 5 | Weight removed (person stepped off) |
| 7 | Jin unit (Chinese unit of weight) |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Weight | service_data[9:11] | Divide by 200 (kg) or 100 (lbs) |
| Stabilized | control_flags bit 4 | True when measurement is final |
| Weight removed | control_flags bit 5 | Person stepped off the scale |
| Unit | control_flags bit 0 | kg vs lbs |
| Timestamp | service_data[2:9] | Year/month/day/hour/minute/second |
| Impedance | service_data[11:13] | v2 only, for body composition |

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Very popular consumer smart scale worldwide
- Only broadcasts after a weight measurement (not continuous)
- Weight data in advertisements is a privacy consideration
- Measurement events are relatively infrequent

## References

- [openScale Xiaomi Mi Scale wiki](https://github.com/oliexdev/openScale/wiki/Xiaomi-Bluetooth-Mi-Scale) — Full protocol documentation
