# Samsung Smart Appliance BLE Protocol

## Overview

Samsung smart appliances (refrigerators, washers, dryers, ovens, etc.) advertise via BLE using company ID 0x0075 (Samsung Electronics). These are distinct from Samsung TV and Galaxy Buds advertisements. The local name often contains a truncated appliance name (e.g., "Refrigerato" for Refrigerator).

## Identifiers

- **Company ID:** `0x0075` (Samsung Electronics Co., Ltd.)
- **Local name:** Varies — appliance name, sometimes truncated (e.g., "Refrigerato", "Samsung CU7000 65")
- **Device class:** `appliance`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0075` | Samsung Electronics |
| Local name | Appliance name | Often truncated to fit BLE ad length |

### Manufacturer Data Structure

Variable length. Two formats observed:

#### Example — Refrigerator (33 bytes)

```
75 00 42 0c 83 45 5d 30 41 4a 54 52 45 31 00 01
04 a4 57 a0 4d a6 02 0a 02 04 36 31 39 56 04 02
04 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `75 00` | Company ID 0x0075 (little-endian) |
| 2 | 1 | `42` | Unknown — possibly device category |
| 3–6 | 4 | `0c 83 45 5d` | Unknown — possibly device identifier |
| 7+ | varies | ... | Contains ASCII-like model info (e.g., "AJTRE1", "619V") |

#### Example — TV (24 bytes)

```
75 00 02 18 34 a1 4f a4 de ff 26 09 3f 21 e7 a3
59 d6 42 da 6e 7f 92 89
```

Shorter format, likely encrypted or hashed device identifier data.

#### Frame type `42 1f` at four lengths (2026-10-06 sweep addition)

The `42 1f` appliance frame is also emitted in short shapes that share
byte6 `00` and the marker `f0 f1` at payload[7..8] (payload offsets after
the 2-byte CID):

```
len 19:  42 1f 2X/3X 01 0X uu 00 f0 f1 01 00 aa aa aa aa 04 02 08 08
len 17:  42 1f 2X/3X/4X 00 0X uu 00 f0 f1 aa aa aa aa 04 02 08 08
len 11:  42 1f 2X/3X 01 0X uu 00 f0 f1 01 00          (len-19 truncated)
len  9:  42 1f 2X/3X/4X 00 0X uu 00 f0 f1             (len-17 truncated)
```

`uu` is a varying unit/state byte; `aa aa aa aa` is a 4-byte ASCII
model-fragment ("075B", "869W", "031V", …); `04 02 08 08` is a constant
trailer. Full history: 49 records / 335 sightings / 29 days
(2026-06-07 → 2026-10-05). Named anchor on the len-17 shape: "Dryer"
(`421f3000002700f0f13836395704020808`). NearSight's `samsung_appliance`
parser claims these as `frame_variant = 421f_short_f0f1` since v1.1;
frames with a broken marker tail (`0f f0 1f`) and the 5–6 byte
`42 1f 50/52 …` stubs are deliberately not claimed.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id | Samsung appliance nearby |
| Appliance type hint | local_name | When available |
| Device category | mfr_data[2] | Needs further analysis |

### What We Cannot Parse (requires GATT connection or SmartThings app)

- Appliance state (running, idle, error)
- Temperature settings
- Cycle status
- Energy usage
- Firmware version

## Identity Hashing

```
identifier = SHA256("samsung_appliance:{mac}")[:16]
```

## Detection Significance

- Indicates a Samsung smart appliance (fridge, washer, TV, etc.)
- Always-on BLE when powered
- Common in households with Samsung SmartThings ecosystem

## References

- Bluetooth SIG company ID: 0x0075 = Samsung Electronics Co., Ltd.
- [Samsung SmartThings](https://www.smartthings.com/) — smart home platform
