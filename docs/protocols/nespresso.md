# Nespresso Coffee Machine BLE Protocol

## Overview

Nespresso connected coffee machines (Vertuo, Venus/VertuoLine) advertise via BLE using company ID 0x0225 and a custom 128-bit service UUID. The BLE connection enables the Nespresso app to read capsule counts, descaling status, and brew settings.

## Identifiers

- **Company ID (SIG-registered):** `0x0225` — Nespresso France SAS
- **Company ID (on-the-wire):** `0x2502` — what shipping firmware actually
  transmits because the bytes are encoded big-endian (a spec violation).
- **Service UUID:** `06AA1910-F22A-11E3-9DAA-0002A5D5C51B` (Nespresso GATT service)
- **Local name pattern:** `{model}_{variant}_{MAC}` (e.g., `Vertuo_CV6_FCB46765786E`)
- **Device class:** `appliance`

### Byte-order quirk (important)

The BLE spec requires company-IDs to be transmitted little-endian, so an
assignment of `0x0225` should appear on the wire as `25 02`. **Every
Nespresso captured to date instead transmits `02 25`** — bytes in
big-endian order. A scanner decoding the manufacturer-data block with
spec-correct LE interpretation therefore reads the company-ID as
`0x2502`, not `0x0225`. The adwatch parser accepts both IDs to tolerate
both correct and broken implementations; in practice only `0x2502` has
ever been observed in the wild.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID (LE-decoded) | `0x2502` | Observed on every real capture |
| Company ID (intent)     | `0x0225` | Nespresso France SAS in SIG registry |
| Service UUID            | `06AA1910-...` | Nespresso app communication service |
| Local name              | `{model}_{MAC}` | Model + MAC address |

### Manufacturer Data Structure

Total: 8 bytes (2 company ID + 6 payload)

#### Examples

```
02 25 40 89 00 00 00 00   (Vertuo CV6)
02 25 00 89 00 00 00 00   (Venus)
02 25 00 09 7f e0 40 00   (Venus variant)
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `02 25` | Company ID — big-endian-encoded 0x0225 (firmware quirk) |
| 2 | 1 | varies | Machine state (bit 6 = ready) |
| 3 | 1 | `89`/`09` | Device type / capability flags |
| 4-7 | 4 | varies | Status data (zeros on every observed capture) |

Byte 2 differs between advertisements: `40` vs `00` confirms bit 6
toggles between ready (`0x40`) and standby (`0x00`). Captures of a Venus
machine at the same address show both states cleanly. Byte 3 (`0x89`)
has been constant across every observed Vertuo / Venus machine.

### Local Name Patterns

| Local Name | Model | Notes |
|------------|-------|-------|
| `Vertuo_CV6_FCB46765786E` | Vertuo Next (CV6) | Last 12 chars = BLE MAC |
| `Venus_D8132A9D825A` | VertuoLine (Venus) | Original VertuoLine model |

### Known Models

| Code | Product |
|------|---------|
| CV6 | Vertuo Next |
| Venus | VertuoLine Original |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id, service_uuid | Nespresso machine nearby |
| Model name | local_name prefix | Product line identification |
| Model code | local_name (e.g., CV6) | Specific model variant |
| MAC address | local_name suffix | Last 12 hex chars |
| Machine state | mfr_data byte 2 | Ready/standby/heating |

### What We Cannot Parse (requires GATT connection or Nespresso app)

- Capsule count
- Descaling status
- Brew settings
- Water tank level
- Error codes

## Identity Hashing

```
identifier = SHA256("nespresso:{mac}")[:16]
```

## Detection Significance

- Indicates a home or office kitchen environment
- Nespresso machines advertise continuously when powered on
- Multiple models may indicate a coffee enthusiast or office break room

## References

- [Nespresso](https://www.nespresso.com/) — manufacturer website
- Service UUID `06AA` base is used across the Nespresso connected range
