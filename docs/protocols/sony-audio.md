# Sony Audio BLE Protocol

## Overview

Sony audio devices (speakers, headphones, earbuds) broadcast BLE advertisements using Sony's company ID and/or service UUID `0xFE2C`. Multiple advertisement formats exist.

**Important:** UUID `0xFE2C` is shared with Google's Find My Device Network (FMDN). The parser must disambiguate — Sony ads have company_id `0x012D` or `fe2c` service data starting with `0x00` or `0x30`.

## Identifiers

- **Company ID:** `0x012D` (Sony Corporation)
- **Service UUID:** `0xFE2C` (Google LLC — shared UUID)
- **Service UUID:** `0xFE03` (Sony Corporation) — used by many LE-only consumer audio modes
- **Service UUID:** `0xFE26` (Sony Corporation) — used by some XM-series headphones for background pairing state
- **Local name patterns:** `LE_SRS-*` (speakers), `LE_WF-*` (earbuds), `LE_WH-*` (headphones), `LE_WI-*` (neckband), `LE_XB-*` / `LE_XE-*` / `LE_XS-*` / `LE_LSPX-*` (speakers); non-`LE_` forms `WH-*`, `WF-*`, `WI-*` also observed
- **Device class:** `speaker`, `headphones`, `earbuds`

## Advertisement Formats

### Format 1: Manufacturer Data (company ID `0x012D`)

20 bytes:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | `0x012D` (LE: `2d01`) |
| 2 | 1 | Protocol version? | `0x04` observed |
| 3 | 1 | Unknown | `0x00` |
| 4-5 | 2 | Device type | `0x0101` — speaker? |
| 6-7 | 2 | Model ID | `0x1004` — SRS-XB33? |
| 8-11 | 4 | Device address | `15afc3d6` |
| 12-13 | 2 | Status | `0206` |
| 14-15 | 2 | State | `c200` |
| 16-19 | 4 | Padding | `00000000` |

### Format 2: Service Data on `fe2c` (frame type `0x00`)

Variable length (6-13 bytes):

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Frame type | `0x00` = Sony device |
| 1 | 1 | Sub-type | `0x90` (speaker), `0x60` (other), `0x00` (simple) |
| 2+ | varies | Payload | Device-specific |

### Format 3: Service Data on `fe2c` (frame type `0x30`)

12 bytes:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Frame type | `0x30` |
| 1-2 | 2 | Unknown | `0000` |
| 3-6 | 4 | Unknown | `00002117` repeating prefix |
| 7-10 | 4 | Rotating ID | Changes between ads |
| 11 | 1 | Counter/state | `0xCA`/`0xC9`/`0xC8` — decrementing |

## Sample Advertisements

```
LE_SRS-XB33 (manufacturer data):
  2d0104000101100415afc3d60206c20000000000

LE_SRS-XB33 (service data on fe2c):
  0090d435499156ec2890ac110e

Anonymous (simple fe2c):
  0000342c50ff
  0000342950ff

Anonymous (type 0x30):
  0030000000211782347fe4ca
  00300000002175b1347fe4c9
```

## Disambiguating from Google FMDN

Both Sony and Google FMDN use service UUID `0xFE2C`. To distinguish:

| Feature | Sony | Google FMDN |
|---------|------|-------------|
| Company ID | `0x012D` | `0x00E0` |
| fe2c data byte 0 | `0x00` or `0x30` | `0x40`+ (FMDN frame types) |
| Local name | `LE_SRS-*`, `LE_WF-*`, `LE_WH-*` | None |
| Manufacturer data | Sony-prefixed | Google-prefixed |

**Rule:** If company_id == `0x012D`, it's Sony. If `fe2c` service data starts with `0x00` or `0x30` and no Google company_id, treat as Sony.

## Device Classification

| Name Pattern | Product Line | Device Class |
|-------------|-------------|-------------|
| `LE_SRS-*` | Sony speakers | speaker |
| `LE_WH-*` / `WH-*` | Sony over-ear headphones | headphones |
| `LE_WF-*` / `WF-*` | Sony true wireless earbuds | earbuds |
| `LE_WI-*` / `WI-*` | Sony neckband headphones | headphones |
| `LE_XB-*` / `LE_XE-*` / `LE_XS-*` | Sony speakers | speaker |
| `LE_LSPX-*` | Sony Lightspeaker | speaker |

## Parsing Strategy

1. Match on company_id `0x012D` OR (service_uuid `fe2c` with Sony-style data)
2. Check for company_id first — if `0x012D`, parse manufacturer data format
3. For `fe2c` service data: check byte 0 for frame type
4. Extract model from local_name (strip `LE_` prefix)
5. Disambiguate from FMDN by checking for Google indicators

## Name-only attribution mode

Some Sony LE-only firmware modes (notably WH-1000XM4/XM5 and several CH-series headphones) broadcast **no manufacturer data and no `FE2C` service data** — only a Sony product name and one of Sony's allocated service UUIDs (`FE03` or `FE26`).

Observed shapes:

```
name=LE_WH-1000XM5  mfg=nil  uuids=[FE03]   svc=nil
name=LE_WH-1000XM4  mfg=nil  uuids=[FE03]   svc={FE26: 3e0a6e}
name=WH-CH720N      mfg=...  uuids=[FE03]   svc=nil
```

**Match rule (safety constraint):** the local name MUST match
`^LE_(SRS|WF|WH|WI|XB|XE|XS|LSPX)-[A-Z0-9]` or the bare form `^(WH|WF|WI)-[A-Z0-9]`,
AND at least one supporting signal must be present — Sony CID `0x012D`, `FE2C`
service data, `FE03` service UUID, or `FE26` service UUID/service data. Name
alone is **not** sufficient (a non-Sony peripheral could advertise a confusable
name).

When this path matches and there's no manufacturer payload, the parser sets
`metadata["match_mode"] = "name_with_sony_uuid"` and **does not** fabricate
`version`/`device_type`/`model_id` fields — only `model` (with `LE_` prefix
stripped) and `deviceClass` (derived from the name prefix).

## References

- Bluetooth SIG Company ID `0x012D` — Sony Corporation
- Bluetooth SIG 16-bit UUID assignment for `0xFE03` — Sony Corporation: https://www.bluetooth.com/specifications/assigned-numbers/
- Sony WH-1000XM5 product page: https://electronics.sony.com/audio/headphones/headband/p/wh1000xm5-b
- Sony Headphones Connect app reverse engineering
- https://github.com/nicholasgasior/sony-headphones-ble (community RE)
