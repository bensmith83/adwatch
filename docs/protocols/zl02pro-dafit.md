# DaFit-family Smartwatch Protocol (ZL02PRO, GW12, …)

## Overview

The **"DaFit family"** is a long-lived white-label Realtek
(**RTL8763E**-class, BT 5.2 dual-mode SoC with audio DSP) smartwatch
firmware shipped under many SKU names — ZL02PRO (round-face
Bluetooth-calling watch), GW12 (small fitness band), plus other
unattributed re-skins. The companion Android/iOS app is **Da Fit** (not
VeryFit).

All variants share three proprietary BLE-layer constants — company ID,
service-data UUID, and the first 2 bytes of mfg data — and disambiguate
themselves with a **3-byte ASCII "variant magic"** at the start of the
FEEA service-data payload:

| Variant magic | ASCII | SKU |
|---------------|-------|-----|
| `44 4B 52`    | `DKR` | ZL02PRO (round-face calling watch) |
| `48 46 55`    | `HFU` | GW12 (small fitness band) |
| *(others)*    | —     | Generic DaFit-family; parser still matches but `model_hint` is nil |

The parser surfaces the 3-byte magic as `metadata.variant` so unknown
SKUs cluster cleanly under one family while we wait for more captures.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | per-variant (`ZL02PRO`, `GW12`, ...) | Optional — useful but not required |
| Company ID | `0xF0EF` (mfg data prefix) | **Not SIG-registered** — squatted |
| Service data UUID | `0xFEEA` | **Not SIG-registered**; SIG record is Swirl Networks (defunct) |
| Variant magic | 3-byte ASCII at FEEA[0..2] | `DKR`, `HFU`, ... |

Note: `0xFEEA` is sometimes mis-attributed to JD.com or Samsung. It is
**not** in the Bluetooth SIG assigned-numbers list as either; the SIG
record assigns it to **Swirl Networks, Inc.** (a US proximity-beacon
vendor that exited the market around 2018). Chinese white-label
firmware vendors squat on the UUID without consequence.

## Ad Format

### Manufacturer Data

```
Offset  Bytes     Meaning
  0-1   ef f0     Company ID 0xF0EF (little-endian, unregistered)
  2-7   xx..xx    6 opaque bytes (observed: eaae5bd0962a)
```

### Service Data (UUID 0xFEEA)

```
Offset  Bytes        Meaning
  0-2   <ASCII>      3-byte variant magic — see table above
  3-N   xx..xx       vendor-proprietary state/counter bytes
```

Observed examples:

| Variant | FEEA payload | Trailing bytes |
|---------|--------------|----------------|
| `DKR` (ZL02PRO) | `44 4B 52 03 04 00 10` | `03 04 00 10` |
| `HFU` (GW12)    | `48 46 55 04 01 00 91` | `04 01 00 91` |

The trailing bytes after the magic have not been fully decoded.
Candidate interpretations (not confirmed): protocol version (byte 3),
payload-type / state byte (byte 4), and a 16-bit counter or status word
(bytes 5..6). The two variants emit different byte-3 values (`03` vs
`04`), suggesting the field is variant-specific rather than a generic
DaFit-family protocol version.

### What We Cannot Parse

- Heart rate, step count (requires GATT connect to DaFit characteristics)
- Firmware version
- Pairing PIN / user ID

## Detection Significance

- Cheap BT-calling smartwatch in range, most commonly paired with the
  Da Fit app
- Same BLE framing is used by other DaFit-SDK watches; we match the
  local-name prefix OR the FEEA+DKR signature

## Parsing Strategy

Single family parser keyed on the AND of three signals (none of which is
unique enough alone):

1. Manufacturer-data CID `0xF0EF` (LE prefix `EF F0`), AND
2. Service data under UUID `0xFEEA` with at least 3 bytes of payload, AND
3. The first 3 bytes of that payload are printable ASCII (the variant
   magic).

Emit:

- `vendor = "DaFit-family (Realtek RTL8763)"`
- `variant = <3-char uppercase ASCII>` (e.g. `DKR`, `HFU`)
- `model_hint = ZL02PRO | GW12 | …` when the variant is known
- `device_class = "wearable"`
- `protocol_payload_hex` — bytes 3..N of the FEEA service data
- `mfg_payload_hex` — bytes 2..N of the manufacturer data

Unknown variant magics still parse — the parser surfaces the magic for
later attribution rather than dropping the row.

## Identity Hashing

```
stable_key = dafit_family:<variant>:<mac>
identifier = SHA256(stable_key)[:16]
```

The variant is included in the key so that two distinct DaFit-family
SKUs that happen to share a MAC (e.g. spoofed or cloned addresses) are
counted as separate identities.

## References

- [Realtek RTL8763E product page](https://www.realtek.com/Product/Index?id=3742&cate_id=194)
- [Example ZL02Pro listing (Kronus / Made-in-China)](https://kronus.en.made-in-china.com/product/YZBtTjgbbpGe/China-Bt-Call-Smartwatch-Rtl8763ewe-One-Click-Connect-1-39-Inch-360-360-HD-Screen-Dafit-APP-Smartwatch-for-Men-Women.html)
- [Nordic bluetooth-numbers-database (SIG CIDs — 0xF0EF absent)](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/company_ids.json)
