# August/Yale Smart Lock

## Overview

August and Yale smart locks broadcast BLE advertisements with device identification and a state-change toggle bit. The actual lock/unlock state requires a GATT connection, but the toggle signals that something changed (useful for event detection).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01D1` (465) | August Home, Inc. |
| Company ID (alt) | `0x012E` (302) | ASSA ABLOY |
| Company ID (alt) | `0x0BDE` (3038) | Yale |
| Service UUID | `0xFE24` | Command service UUID |
| Local name | 7-char pattern | First 2 + last 5 chars of serial (e.g., `A112345`) |

### Manufacturer Data Layout

**August/Yale data (company ID 0x01D1):**

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | State toggle | uint8 | `0x00` or `0x01` — toggles on state change | — |

The toggle byte alternates between 0 and 1 whenever the lock state changes. It does NOT indicate locked vs unlocked — just that a change occurred.

**HomeKit data (company ID 0x004C, if present):**
- First byte `0x06` = unencrypted HAP, `0x11` = encrypted HAP
- Contains HomeKit state number that changes on lock events

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | Company ID / Service UUID | August/Yale lock nearby |
| State change signal | mfr_data[0] | Toggle bit — something changed |
| Serial hint | Local name | 7-char derived from serial |
| HomeKit presence | Apple mfr_data | If HomeKit is configured |

### What Requires GATT Connection

- Lock/unlock state
- Door open/close state
- Battery level
- Firmware version
- Full serial number

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Detection Significance

- Very popular smart lock brand (millions installed)
- Presence detection = smart lock nearby
- State toggle enables basic event detection without knowing the actual state
- HomeKit integration visible in ads

## References

- [yalexs-ble](https://github.com/Yale-Libs/yalexs-ble) — Python BLE library
