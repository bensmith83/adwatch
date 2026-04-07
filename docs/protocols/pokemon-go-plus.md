# Pokemon GO Plus + BLE Protocol

## Overview

The Pokemon GO Plus + (PGP+) is a Nintendo gaming accessory for the Pokemon GO mobile game. It advertises via BLE using company ID 0x0553 (Nintendo Co., Ltd.) and the local name "Pokemon GO Plus +". It also advertises a custom service UUID `138C35B6` for game communication.

## Identifiers

- **Company ID:** `0x0553` (Nintendo Co., Ltd.)
- **Local name:** `Pokemon GO Plus +`
- **Service UUID:** `138C35B6` (custom, partial — likely 128-bit)
- **Device class:** `gaming_accessory`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0553` | Nintendo Co., Ltd. |
| Local name | `Pokemon GO Plus +` | Fixed string |
| Service data UUID | `138C35B6` | Custom UUID with empty data payload |

### Manufacturer Data Structure

Total: 17 bytes (2 company ID + 15 payload)

#### Example

```
53 05 01 ae de 00 f0 be 00 00 00 00 00 00 00 00 02
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `53 05` | Company ID 0x0553 (Nintendo, little-endian) |
| 2 | 1 | `01` | Unknown — possibly protocol version |
| 3–4 | 2 | `ae de` | Unknown — possibly device ID |
| 5 | 1 | `00` | Unknown |
| 6–7 | 2 | `f0 be` | Unknown — possibly session or pairing token |
| 8–14 | 7 | `00...00` | Padding / reserved |
| 15 | 1 | `00` | Unknown |
| 16 | 1 | `02` | Unknown — possibly device state |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id or local_name | PGP+ accessory nearby |
| Device type | local_name | "Pokemon GO Plus +" |

### What We Cannot Parse (requires GATT connection)

- Connection state with phone
- Button press events
- Catch/spin notifications
- Battery level
- Firmware version

## Identity Hashing

```
identifier = SHA256("pokemon_go_plus:{mac}")[:16]
```

## Detection Significance

- Indicates a Pokemon GO player nearby with a PGP+ accessory
- Active BLE advertisement when powered on and not connected to phone
- Battery-powered device, may not always be broadcasting

## References

- Bluetooth SIG company ID: 0x0553 = Nintendo Co., Ltd.
- [Pokemon GO Plus +](https://www.pokemongolive.com/pokemon-go-plus-plus) — product page
