# Marshall Audio BLE Protocol

## Overview

Marshall Bluetooth speakers broadcast BLE advertisements using the CSR/Qualcomm service UUID `0xFE8F` and Qualcomm Technologies International company ID `0x0912`. These speakers use CSR Bluetooth chipsets common across many premium audio brands.

## Identifiers

- **Service UUID:** `0xFE8F` (16-bit, assigned to CSR plc / Qualcomm)
- **Company ID:** `0x0912` (Qualcomm Technologies International, Ltd.)
- **Local name:** Full product names (e.g. "STANMORE II", "EMBERTON", "KILBURN II")
- **Device class:** `speaker`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE8F` | CSR / Qualcomm assigned UUID |
| Company ID | `0x0912` | Qualcomm Technologies International |
| Local name | Product name | e.g. "STANMORE II", "EMBERTON" |

**Note:** UUID `0xFE8F` is a CSR/Qualcomm UUID used by many audio devices with CSR Bluetooth chips. Marshall devices are identified by the combination of this UUID with recognizable Marshall product names in the local name.

### Manufacturer Data Format

Variable length, company_id `0x0912` (LE: `1209`):

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | `0x0912` (LE: `1209`) |
| 2+ | varies | CSR payload | Chipset-specific data |

The manufacturer data contains CSR/Qualcomm chipset information but is not Marshall-specific. Useful fields are limited to device presence identification.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or company_id | Marshall speaker nearby |
| Model name | local_name | Full product name |
| Speaker type | local_name | Home vs. portable form factor |

### What We Cannot Parse (requires GATT)

- Battery level
- Firmware version
- EQ settings
- Playback state (playing, paused)
- Volume level
- Multi-speaker grouping status

## Known Models

| Local Name | Product | Form Factor |
|-----------|---------|-------------|
| `STANMORE II` | Marshall Stanmore II | Home speaker |
| `ACTON II` | Marshall Acton II | Compact home speaker |
| `WOBURN II` | Marshall Woburn II | Large home speaker |
| `EMBERTON` | Marshall Emberton | Portable speaker |
| `EMBERTON II` | Marshall Emberton II | Portable speaker |
| `KILBURN II` | Marshall Kilburn II | Portable speaker |
| `MIDDLETON` | Marshall Middleton | Portable speaker |
| `WILLEN` | Marshall Willen | Ultra-compact portable |
| `STOCKWELL II` | Marshall Stockwell II | Portable speaker |

## Sample Advertisements

```
STANMORE II:
  Service UUID: fe8f
  Local name: STANMORE II
  Manufacturer data: 1209 04a3b7c4e8f2

EMBERTON:
  Service UUID: fe8f
  Local name: EMBERTON
  Manufacturer data: 1209 04f8d2a1b6c9

KILBURN II:
  Service UUID: fe8f
  Local name: KILBURN II
  Manufacturer data: 1209 04c7e5f3a2d8
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

Marshall speakers use a static BLE MAC address, making this a stable identifier.

## Detection Significance

- Indicates presence of premium audio equipment
- Model name reveals specific product and form factor (home vs. portable)
- Always-on BLE when speaker is powered on
- CSR/Qualcomm UUID is shared with other audio brands -- local name is the key differentiator for Marshall

## Parsing Strategy

1. Match on service_uuid `fe8f` AND/OR company_id `0x0912`
2. Check local_name against known Marshall product names
3. Extract model name from local_name
4. Return device class `speaker`
5. Note: other audio brands also use `fe8f` -- may need local_name allowlist for Marshall-specific identification

## References

- [Marshall](https://www.marshallheadphones.com/) -- manufacturer website
- [Bluetooth SIG Company IDs](https://www.bluetooth.com/specifications/assigned-numbers/) -- `0x0912` Qualcomm Technologies International, Ltd.
- Bluetooth SIG UUID Database -- UUID `0xFE8F` assigned to CSR plc
