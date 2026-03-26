# EcoFlow (Portable Power Stations)

## Overview

EcoFlow Delta, River, and PowerStream devices broadcast BLE advertisements for device discovery and pairing. Advertisements contain device identification (serial number, product type) but rich telemetry (battery level, power data) requires an authenticated connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xB5B5` | Custom/unregistered, used across all EcoFlow BLE devices |
| Local name | `EF-*` | Prefix `EF-` followed by serial number chars |

### Manufacturer Data Layout

| Offset | Size | Field | Encoding | Notes |
|--------|------|-------|----------|-------|
| 0 | 1 | Protocol version | uint8 | |
| 1-16 | 16 | Serial number | ASCII | e.g. `R331xxxxxxxxxxxx` |
| 17 | 1 | Status | uint8. Bit 7 = active flag | |
| 18 | 1 | Product type | uint8 | |
| 19-21 | 3 | Reserved | — | |
| 22 | 1 | Capability flags | bitfield (see below) | |

If manufacturer data < 20 bytes, defaults: status=0, product_type=0.

### Capability Flags (byte 22)

| Bits | Mask | Field |
|------|------|-------|
| 0 | `0x01` | Encrypted communication |
| 1 | `0x02` | Supports verification |
| 2 | `0x04` | Verified/paired |
| 3-5 | `0x38` >> 3 | Encryption type (0–7) |
| 6 | `0x40` | Supports 5GHz WiFi |

### Serial Number Prefixes → Device Model

| Prefix | Device |
|--------|--------|
| `R331`/`R335` | DELTA 2 |
| `R351`/`R354` | DELTA 2 Max |
| `P231` | DELTA 3 |
| `D3N1` | DELTA 3 Classic |
| `DCA`/`DCF`/`DCK` | DELTA Pro |
| `MR51` | DELTA Pro 3 |
| `Y711` | DELTA Pro Ultra |
| `R601`/`R603` | RIVER 2 |
| `R611`/`R613` | RIVER 2 Max |
| `R631`/`R634` | RIVER 3 Plus |
| `HW51` | PowerStream |
| `HD31` | Smart Home Panel 2 |
| `DB` | DELTA mini |

(Many more prefixes exist — see ha-ef-ble source for full mapping.)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device present | company_id match | EcoFlow device nearby |
| Serial number | bytes 1–16 | ASCII, identifies specific unit |
| Device model | serial prefix | Map prefix → product name |
| Active state | byte 17, bit 7 | Device awake/active |
| Encryption status | byte 22 | Whether BLE comms are encrypted |

### What We Cannot Parse from Advertisements

- Battery level / state of charge
- Charge/discharge power (watts)
- AC/DC/USB port states
- Temperature
- Solar input

All telemetry requires authenticated GATT connection with ECDH key exchange + AES-CBC encryption.

## References

- **RE repo**: https://github.com/rabits/ef-ble-reverse
- **HA integration**: https://github.com/rabits/ha-ef-ble
- **Delta 2 RE**: https://github.com/nielsole/ecoflow-bt-reverse-engineering
