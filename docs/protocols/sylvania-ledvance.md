# Sylvania/LEDVANCE Smart Light BLE Protocol

## Overview

Sylvania and LEDVANCE smart lights advertise via BLE using the assigned service UUID FDC1 and company ID 0x0819. Sylvania devices use the local name prefix `SIL:` while LEDVANCE devices use `DUE:`, each followed by a 4-character hex device identifier.

## Identifiers

- **Service UUID:** `FDC1` (16-bit, Bluetooth SIG assigned)
- **Company ID:** `0x0819` (Sylvania/LEDVANCE)
- **Local name pattern:** `SIL:XXXX` (Sylvania) or `DUE:XXXX` (LEDVANCE)
- **Device class:** `smart_light`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FDC1` | Bluetooth SIG assigned |
| Company ID | `0x0819` | Sylvania/LEDVANCE |
| Local name | `SIL:XXXX` or `DUE:XXXX` | Brand prefix + hex device ID |

### Manufacturer Data Structure

Total: 11 bytes (2 company ID + 9 payload)

#### Example — Sylvania (SIL:4914)

```
19 08 8a 6c 17 00 00 00 00 00 c2
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `19 08` | Company ID 0x0819 (little-endian) |
| 2–5 | 4 | `8a 6c 17 00` | Unknown — possibly device type/firmware |
| 6–9 | 4 | `00 00 00 00` | Unknown — possibly state/status (all zeros) |
| 10 | 1 | `c2` | Status or flags byte |

#### Example — LEDVANCE (DUE:1568)

```
19 08 11 60 09 40 0b 00 00 00 c2
```

Same structure, different payload values at offsets 2–9. The trailing `c2` byte is consistent across both brands.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Smart light nearby |
| Brand | local_name prefix | SIL = Sylvania, DUE = LEDVANCE |
| Device ID | local_name suffix | 4-char hex identifier |

### What We Cannot Parse (requires GATT connection)

- Light on/off state
- Brightness level
- Color temperature / RGB values
- Firmware version
- Wi-Fi/mesh configuration

## Identity Hashing

```
identifier = SHA256("sylvania_ledvance:{mac}")[:16]
```

## Detection Significance

- Indicates a Sylvania or LEDVANCE smart light in the area
- Always-on BLE advertisement when powered
- Common in smart home setups

## References

- Bluetooth SIG 16-bit UUID assignment: FDC1
- [LEDVANCE](https://www.ledvance.com/) — manufacturer website
- [Sylvania Smart+](https://www.sylvania-home.com/) — consumer smart lighting
