# Garmin Wearable Plugin

## Overview

Garmin is one of the most popular wearable/fitness device manufacturers. Their watches and fitness trackers (Forerunner, Fenix, Venu, Vivoactive, Lily, Instinct) advertise over BLE for phone connectivity and sensor broadcasting. Garmin watches are extremely common — nearly every runner/cyclist in a neighborhood has one.

## Supported Device Families

| Family | Example Models | Local Name Pattern |
|--------|---------------|-------------------|
| Forerunner | 55, 165, 255, 265, 745, 945, 965 | `Forerunner *` or `FR*` |
| Fenix | 6, 7, 8 | `fenix *` |
| Venu | Venu, Venu 2, Venu 3, Venu Sq | `Venu*` |
| Vivoactive | 4, 5 | `vivoactive*` or `VA*` |
| Instinct | 1, 2, 3, Crossover | `Instinct*` |
| Lily | 1, 2 | `Lily*` |
| Vivosmart | 4, 5 | `vivosmart*` |
| Edge | 530, 540, 830, 840, 1040, 1050 | `Edge *` |
| HRM | HRM-Pro, HRM-Dual | `HRM-*` |
| Index | Index S2 (smart scale) | `Index*` |
| Vivomove | Trend, Style | `vivomove*` |

## BLE Advertisement Format

### Identification

Garmin devices can be identified by:

1. **Company ID**: `0x0087` (Garmin International, Inc. — decimal 135)
2. **Local Name Pattern**: Model family names listed above
3. **Service UUID**: May advertise standard GATT services like Heart Rate (`0x180D`)

Best match strategy: `company_id=0x0087` (catches all Garmin devices regardless of name).

### Manufacturer Data (Company ID 0x0087)

```
Offset  Length  Field            Description
0       2       Company ID       0x8700 (LE) = 0x0087
2       var     Payload          Layout-specific (see below)
```

The manufacturer data format varies by device family. The named
sport-watch advertisement carries a short body (often one byte) next to
the local name; the dash cams carry their own 8-byte body (see
`garmin-dashcam.md`); and the nameless frames below carry the product
number.

### Nameless product-ID frame (2026-08-29 sweep)

A Garmin device advertising with **no local name** — the common case for
a watch that is already paired to its owner's phone — sends one of two
short frames whose first two post-CID bytes are the device's FIT-profile
**`garmin_product` number, big-endian**:

```
87 00 | PP PP                   2-byte frame            87 00 11 b8  → 4536 = fenix8
87 00 | PP PP | 00 00 00        5-byte, zero-padded     87 00 11 ae 00 00 00 → 4526 (not in the public enum)
```

The padded layout was seen only on units that also advertise Garmin's SIG
member service UUID `0xFE1F` (19 units in one afternoon, 2026-08-28); the
bare 2-byte layout appears with and without FE1F.

Evidence for the reading: of the 24 distinct 2-byte values in the merged
telemetry corpus, 13 map exactly onto Garmin's own FIT SDK enum and every
one of them is a mainstream consumer watch —

| Bytes | Number | FIT identifier |
|-------|--------|----------------|
| `0f 43` | 3907 | `fenix7x` |
| `0f b8` | 4024 | `fr955` |
| `10 a1` | 4257 | `fr265_large` |
| `11 50` | 4432 | `fr165` |
| `11 b8` | 4536 | `fenix8` |
| `0c 36` | 3126 | `instinct_esports` |
| `0c d2` | 3282 | `fr45` |
| `09 7f` | 2431 | `fr235` |
| `08 6e` | 2158 | `fr735xt` |
| `0c 05` | 3077 | `fr245_music` |
| `0f 96` | 3990 | `fr255_music` |
| `0c 98` | 3224 | `vivoactive4_small` |
| `11 4a` | 4426 | `vivoactive5` |

— while the little-endian reading of the same bytes (0x360c, 0xb811, …)
lands nowhere in the enum's range. The unmapped values (3393, 3491, 3534,
3540, 3962, 4012, 4161, 4209, 4422, 4495, 4526, 4527) sit in the enum's
gaps — the public enum lags regional SKUs and the newest releases (4526 /
4527 fall between `rally_x10` 4525 and `fenix8_solar` 4532) — and one of
them, 3540, was advertised by a unit named `CAD-BLE…` next to the Cycling
Speed and Cadence service, i.e. a cadence sensor, so the number space is
not watches-only.

Parser behaviour (`garmin` v1.2): on the two layouts above the nameless
path emits `product_id` (decimal), `product_id_hex`, `frame_layout`
(`product_id` / `product_id_padded`) and, when the vendored enum knows the
number, `product_name` (the SDK identifier, verbatim) with
`product_name_source = fit_sdk_garmin_product` and `product_known = true`;
an unknown number is reported with `product_known = false` and no name is
invented. Other lengths, a non-zero tail on the 5-byte frame, and a zero
number stay raw. A product number is per-model, never per-unit, so
identity is unchanged (MAC-derived, no stable key). The legacy
`message_type` key (first payload byte, decimal) is still emitted for
continuity; on these frames it is simply the number's high byte.

Enum source: Garmin FIT Python SDK, `garmin_fit_sdk/profile.py`, type
`garmin_product` (fetched 2026-08-29; 496 entries), vendored as
`GarminProductCatalog` in the app.

Confidence: **high** on the reading (13/24 exact hits on popular models,
zero hits little-endian); no in-corpus named unit has yet been captured
alongside its product-ID frame, so a name↔number confirmation from a
live capture remains the one missing check.

### Common Service UUIDs

Garmin devices may advertise these standard BLE services:
- `0x180D` — Heart Rate (HRM straps)
- `0x1816` — Cycling Speed and Cadence (Edge devices)
- `0x1818` — Cycling Power
- `0x180F` — Battery Service
- `6A4E####-667B-11E3-949A-0800200C9A66` — Garmin proprietary service base

### Parser Strategy

- Register with `company_id=0x0087`
- Extract device family/model from local_name if available
- Parse manufacturer data for device type and state
- Identify HRM vs watch vs cycling computer from service UUIDs
- Return ParseResult with device_type, model_family, and any extractable state

## References

- [Garmin Connect IQ SDK](https://developer.garmin.com/connect-iq/)
- [Bluetooth SIG Company ID 0x0087](https://www.bluetooth.com/specifications/assigned-numbers/)
- [ANT+ / BLE Garmin Sensors](https://www.thisisant.com/developer/ant-plus/ant-plus-basics/)
- [nRF Connect profiles for Garmin devices](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)
