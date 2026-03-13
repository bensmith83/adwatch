# MEATER (Wireless Meat Thermometer)

## Overview

MEATER is a premium wireless meat thermometer probe by Apption Labs. The probe broadcasts its presence via BLE but all temperature data requires a GATT connection. This parser provides device detection only.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x037B` (891) | Apption Labs Inc. |
| Local name | `MEATER` | Exact match |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | Company ID / local name | MEATER probe nearby |

### What Requires GATT Connection

- Tip temperature (internal meat temp)
- Ambient temperature (cook/oven temp)
- Battery level
- Probe ID / firmware version
- Temperature history (512-byte ring buffer)

**Note:** The probe only allows a single BLE connection. If the MEATER app is connected, the probe won't be discoverable.

## Identity Hashing

```
identifier = SHA256("{mac}:MEATER")[:16]
```

## Detection Significance

- Indicates active cooking/grilling session
- Premium product = distinctive presence
- Detection-only but fun metadata (someone's grilling!)

## References

- [nathanfaber/meaterble](https://github.com/nathanfaber/meaterble) — Reverse-engineered BLE protocol
