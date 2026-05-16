# VeryFit / ID115 Fitness Band

## Overview

The **ID115 / ID115 Plus / ID115 HR** is a cheap (~$15 — $30) Chinese
fitness band manufactured by Shenzhen DO Intelligent Technology Co.,
sold under the **VeryFit** app branding and re-badged under dozens of
white-label brand names on Amazon and AliExpress (Yamay, Lintelek,
LETSCOM, MorePro, etc.).

It uses an off-the-shelf **Aplix Corporation** Bluetooth module
(company ID `0x0173`) — Aplix is a Japanese BLE-module house whose
silicon shows up in many low-cost wearable + IoT products. The same
mfr-data layout (`73 01 <8 bytes>`) appears across all VeryFit-app
compatible bands regardless of the cosmetic brand on the package.

The Realtek `0x0AF0` service-data parser (`realtek-fitness-0af0.md`)
covers a different but adjacent product family — Realtek-chipset
bands that also use VeryFit. The two protocols share the `0x0AF0`
service UUID but differ in manufacturer data:

| Family | Mfr CID | Service UUID | Local-name prefix |
|--------|---------|--------------|-------------------|
| VeryFit / Aplix | `0x0173` | `0AF0` | `ID115*`, `ID130*`, `ID152*` (model code) |
| Realtek-chipset | (none / vendor-specific) | `0AF0` | varies — `M3`, `M4`, white-label codes |

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0173` | Aplix Corporation (BT SIG) |
| Service UUID | `0AF0` | "VeryFit" service UUID family |
| Local name | `^ID\d{3}(Plus)?(HR)?$` with optional trailing spaces | e.g. `ID115Plus HR ` |

Captured in adwatch:

```
Local name: "ID115Plus HR "  (note the trailing space — included by firmware)
Mfr data:   73 01 e4 ec 4d 90 bf 3d
            └─┬─┘ └─────────┬─────────┘
             cid     6-byte payload
Svc UUIDs:  [0AF0]
```

## Manufacturer Data

| Offset (post-cid) | Bytes | Meaning |
|-------------------|-------|---------|
| 0–5               | `e4 ec 4d 90 bf 3d` | Device identifier — appears to be a MAC-derived hash |

The 6-byte payload is fixed per physical band — it does **not**
encode live sensor readings (heart rate, steps, battery). All live
data is delivered via GATT notifications on a paired session.

## Supported Models

| Local name | Hardware |
|------------|----------|
| `ID115`    | Original ID115 |
| `ID115 HR` | ID115 with heart-rate sensor |
| `ID115Plus HR ` | ID115 Plus HR (trailing space in capture) |
| `ID130`    | ID130 (variant) |
| `ID152`    | ID152 (variant) |

Other model codes (`ID11X` etc.) should be picked up automatically by
the regex.

## Identity Hashing

```
identifier_hash = SHA256("veryfit:{model}:{mfr_payload_hex}")[:16]
```

Using the 6-byte mfr payload as part of the identity is appropriate
because (a) it's stable per unit and (b) it distinguishes two
identical models in the same room — unlike a MAC, which rotates on
some firmware variants.

## What We Cannot Parse Without GATT

- Heart rate (live BPM)
- Step count
- Battery percent
- Calorie estimate
- Sleep state
- Active workout mode

All of those flow over GATT notifications and require a paired
VeryFit-app session.

## References

- VeryFit by Veryfitpro app: https://veryfitpro.com
- ID115 Plus HR FCC user manual: https://images-na.ssl-images-amazon.com/images/I/81GJQruUoxS.pdf
- Bluetooth SIG company ID `0x0173` → Aplix Corporation
- ID115 community thread (XDA Forums): https://xdaforums.com/t/veryfit-id115-hr.3820063/
