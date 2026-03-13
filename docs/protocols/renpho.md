# Renpho / Etekcity Smart Scale

## Overview

Renpho and Etekcity smart scales (and many white-label clones) use the QN protocol over BLE. Devices broadcast their presence but all weight/body composition data requires a GATT connection. This parser provides device detection only.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x06D0` (1744) | Etekcity Corporation |
| Local name | `QN-Scale` | Shared across many brands |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | Company ID / local name | Smart scale nearby |

### What Requires GATT Connection

- Weight (kg/lbs)
- Body fat percentage
- BMI, muscle mass, bone mass
- Body water percentage
- All data via QN protocol on service `0xFFE0` / characteristic `0xFFE1`

### Known Brands Using QN Protocol

Many brands share the same `QN-Scale` local name and protocol:
- Renpho (ES-CS20M, ES-30M, ES-26M)
- Etekcity (ESF-551)
- FitIndex
- Kamtron
- 1byone
- Arboleaf

## Identity Hashing

```
identifier = SHA256("{mac}:QN-Scale")[:16]
```

## Detection Significance

- Very common household device
- Many different brands share the same protocol
- Detection-only but indicates health/fitness tracking interest

## References

- [openScale — QN Scale](https://github.com/oliexdev/openScale) — BluetoothQNScale driver
- [Home Assistant Etekcity integration](https://community.home-assistant.io/t/etekcity-fitness-scale-ble-custom-integration/765551)
