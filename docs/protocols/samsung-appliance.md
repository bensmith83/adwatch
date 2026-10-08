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
75 00 42 xx xx xx xx 30 41 4a 54 52 45 31 00 01
04 a4 57 a0 4d a6 02 0a 02 04 36 31 39 56 04 02
04 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0–1 | 2 | `75 00` | Company ID 0x0075 (little-endian) |
| 2 | 1 | `42` | Unknown — possibly device category |
| 3–6 | 4 | `xx xx xx xx` | Unknown — possibly device identifier |
| 7+ | varies | ... | Contains ASCII-like model info (e.g., "AJTRE1", "619V") |

#### Example — TV (24 bytes)

```
75 00 02 18 xx xx xx xx xx xx xx xx xx xx xx xx
xx xx xx xx xx xx xx xx
```

Shorter format, likely encrypted or hashed device identifier data.

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
