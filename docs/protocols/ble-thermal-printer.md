# BLE Thermal Printer Protocol (cat printer family)

## Overview

A large family of cheap Bluetooth-connected thermal / receipt / label printers
share a common BLE signature. Model names include:

- **Cat printers** (viral pocket receipt printers): GB01, GB02, GB03
- **GOOJPRT**: PT-210, PT-220, MTP-2, MTP-3
- **PeriPage+**: A6, A9, and variants
- **Other re-brands**: GT01, MX05/06, YT01, **GLI1050**, ...

These devices expose a Nordic-uC-hosted firmware with a proprietary GATT
service for sending ESC/POS-style raster data, plus the standard Nordic
DFU service for firmware updates. All observed variants in the wild
advertise the same 128-bit vendor service UUID.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Vendor service UUID | `e7810a71-73ae-499d-8c15-faa9aef0c3f2` | **Distinctive** — the primary identifier |
| DFU service UUID | `0x18F0` | Nordic DFU; not unique to printers |
| Local name | model-dependent | See model table |
| Company ID (mfg data) | variable / unregistered | `0x031E` observed (Eyefi — likely reused) |

## Model Name Regex

```
^(GB0[123]|GT0[12]|MX0[0-9]|PT-?2[01]0|MTP-?[23]|PeriPage|YT01|GLI\d{3,4})
```

Sample observed names: `GB01`, `GB03`, `PT-210`, `MTP-3`, `PeriPage A6`,
`GLI1050.I`.

## Ad Format

The advertisement is a connection invitation — there is typically no useful
payload in the mfg data. All meaningful interaction happens after a GATT
connection. What we can extract passively:

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service UUID | Printer nearby |
| Model | local_name | Extracted via regex group |
| Identity | MAC address | Usually static public MAC |

## What We Cannot Parse (requires GATT connection)

- Firmware version
- Paper status / battery
- Print-head temperature
- Spooler queue

## Detection Significance

- Receipt / label printer in range — often left advertising even when idle
- Common in retail, POS setups, hobbyist maker scenes, and in Etsy-style
  sticker/label shops
- `GLI1050` in particular was misidentified in our initial export as an
  ignition-interlock device; the UUID signature is the tiebreaker

## Identity Hashing

```
identifier = SHA256("{mac}:thermal_printer")[:16]
```

## Parsing Strategy

1. Match on vendor UUID `e7810a71-...` OR on DFU UUID `0x18F0` OR on a
   known model-name prefix.
2. Reject ads that only carry `0x18F0` (too generic — many Nordic-based
   devices use DFU) unless a name or vendor UUID is also present.
3. Extract the model family from `local_name` when available.

## References

- [bitbank2/Thermal_Printer (Arduino library; uses `0x18F0` service)](https://github.com/bitbank2/Thermal_Printer)
- [WerWolv — "Reverse engineering a cat printer"](https://werwolv.net/blog/cat_printer)
- [lisp3r/bluetooth-thermal-printer (RE notes for GB01/02/03)](https://github.com/lisp3r/bluetooth-thermal-printer)
- [NaitLee/Cat-Printer (open-source driver)](https://github.com/NaitLee/Cat-Printer)
- FCC ID `2AQWW-GLI1050B` — Yancheng Tianyuan Lamp Mfg, the apparent OEM for the GLI1050 family
