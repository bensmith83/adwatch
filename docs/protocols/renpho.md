# Renpho / Etekcity / Levoit Smart-Home Family

## Overview

Bluetooth SIG **company ID `0x06D0`** is registered to **Etekcity
Corporation**, the parent company of three consumer-product brands
that all share the same BLE advertisement framing:

| Brand   | Product family       | Local-name prefix          |
|---------|----------------------|----------------------------|
| Renpho  | Body-composition scales | `QN-Scale`, `Renpho*` |
| Levoit  | Air purifiers        | `Core200s`, `Core300s`, `Core400s`, `Core600s` |
| Levoit  | Humidifiers          | `classic300s`, `classic200s`, `Dual200s`, `OasisMist*` |
| Levoit  | Vital purifier line  | `Vital100s`, `Vital200s` |
| Etekcity| Kitchen / smart scales | `Etekcity*`, `ESN*` |

The advertisement is identification-only — live data (weight, fan
speed, water level, ambient air quality, etc.) requires a paired
GATT session.

### Company ID `0x0157` is Huami, not Qingniu (corrected 2026-09-30)

An earlier version of the `renpho` plugin also claimed CID `0x0157` as
"Qingniu's SIG-assigned CID" and decoded a live weight preview (LE16 weight
/ unit nibble / stable bit / embedded MAC) from it. That attribution was
wrong: the [Bluetooth SIG Assigned Numbers registry](https://bitbucket.org/bluetooth-SIG/public/src/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
(and adwatch's own `_bt_company_ids.py`) assigns `0x0157` to **Anhui Huami
Information Technology Co., Ltd.** (Zepp / Amazfit). All six `0x0157` frames
in the NearSight telemetry corpus are Huami wearables
(`57 01 02 ...`, handled by `huami_amazfit` — see `huami-amazfit.md`), and
the weight decode mislabelled them as scales. The plugin now matches only
CID `0x06D0`, the Qingniu/Yolanda name catalog and the scale service UUIDs;
no Qingniu manufacturer-data weight preview is decoded.

## Wire Format

```
d0 06 | 01 | de f2 b2 be 5b c4 | c6 | 2c | 02 02 02
└─┬─┘   └┬┘   └────────┬───────┘   └┬┘   └┬┘   └──┬──┘
 cid    op     device id (6B)      sep   product   trailer
                                          token
```

| Offset (post-cid) | Bytes        | Meaning |
|-------------------|--------------|---------|
| 0                 | `01`         | Opcode / frame type (constant `0x01` observed) |
| 1–6               | `def2b2be5bc4` | Per-unit device identifier (MAC-derived hash, stable per physical device) |
| 7                 | `c6`         | Separator / config byte (constant observed) |
| 8                 | `2c`         | Product token — distinguishes SKUs (e.g. `0x2C`=Core 400S, `0x25`=Classic 300S) |
| 9–11              | `02 02 02`   | Trailer (constant observed) |

### Captured product-token mapping

| Token | Product (inferred from local name) |
|-------|------------------------------------|
| `0x2C` | Levoit Core 400S air purifier |
| `0x25` | Levoit Classic 300S humidifier |

Other tokens not yet observed; the field is exposed as
`product_token` for future characterisation.

## Identity Hashing

```
identifier_hash = SHA256("renpho:{device_id_hex}")[:16]
```

The 6-byte `device_id` is stable per physical unit and survives MAC
rotation, so it provides reliable per-unit identity without depending
on the BLE MAC.

## Brand / Device-class Classification

The parser inspects the **local name** to assign `brand` and
`deviceClass` metadata:

| Local-name prefix | brand | deviceClass |
|-------------------|-------|-------------|
| `QN-Scale`, `Renpho` | Renpho | `scale` |
| `Core`            | Levoit | `air_purifier` |
| `Classic`, `Dual`, `Oasis` | Levoit | `humidifier` |
| `Vital`, `Sprout` | Levoit | `air_purifier` |
| `Etekcity`, `ESN` | Etekcity | `scale` |
| (other)           | Etekcity Corp | `smart_home` |

## What Requires GATT Connection

### Renpho scales (QN protocol on service 0xFFE0 / characteristic 0xFFE1)
- Weight (kg/lbs)
- Body fat / muscle / bone / water percentages
- BMI

### Levoit appliances (Vesync app)
- Fan speed / mode (purifier)
- Mist level (humidifier)
- Filter / water-tank state
- Air-quality sensor reading (purifier with AQ sensor)

## Known White-label Renpho Clones (QN protocol)

Many brands share the `QN-Scale` local name and QN GATT protocol:
- Renpho (ES-CS20M, ES-30M, ES-26M)
- Etekcity (ESF-551)
- FitIndex
- Kamtron
- 1byone
- Arboleaf

## References

- Bluetooth SIG company ID `0x06D0` → Etekcity Corporation
- VeSync app (Levoit + Etekcity controller): https://vesync.com
- [openScale — QN Scale driver](https://github.com/oliexdev/openScale)
- [Home Assistant Etekcity integration](https://community.home-assistant.io/t/etekcity-fitness-scale-ble-custom-integration/765551)
