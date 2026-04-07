# PR BT Portable Bluetooth Device Protocol

## Overview

PR BT devices advertise via BLE with a custom 128-bit service UUID `4553867F-F809-49F4-AEFC-E190A1F459F3` alongside the standard Device Information service (180A). The local name follows the pattern "PR BT XXXX" where XXXX is a hex device identifier. The "PR BT" prefix suggests a portable Bluetooth device, possibly a printer or peripheral.

## Identifiers

- **Service UUID:** `4553867F-F809-49F4-AEFC-E190A1F459F3` (custom 128-bit)
- **Standard service:** `180A` (Device Information)
- **Local name pattern:** `PR BT XXXX` (XXXX = hex device ID, e.g., `PR BT 06CD`)
- **Device class:** `peripheral`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `4553867F-F809-49F4-AEFC-E190A1F459F3` | Custom 128-bit UUID |
| Standard service | `180A` | Device Information Service |
| Local name | `PR BT XXXX` | Hex device identifier suffix |

### Advertisement Contents

These advertisements are minimal:
- **No manufacturer data** — no company ID or payload
- **No service data** — UUIDs advertised but with no associated data
- **Address type:** random

The device advertises two service UUIDs:
1. `180A` — Standard BLE Device Information Service (exposes model, serial, firmware via GATT)
2. `4553867F-F809-49F4-AEFC-E190A1F459F3` — Custom service for device-specific communication

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | PR BT device nearby |
| Device ID | local_name suffix | 4-char hex identifier |

### What We Cannot Parse (requires GATT connection)

- Device type / model
- Device information (via 180A GATT service)
- Device-specific functionality
- Battery level
- Firmware version

## Identity Hashing

```
identifier = SHA256("pr_bt:{mac}")[:16]
```

## Detection Significance

- Indicates a portable Bluetooth peripheral device
- "PR" prefix may indicate a portable printer or similar device
- Consistent BLE advertisement when powered on

## References

- Device identified from BLE scan data
- Service UUID `4553867F-F809-49F4-AEFC-E190A1F459F3` appears to be a vendor-specific assignment
- `180A` is the standard Bluetooth Device Information Service
