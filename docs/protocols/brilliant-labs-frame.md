# Brilliant Labs Frame (AI Smart Glasses)

## Overview

Brilliant Labs **Frame** are open-source, BLE-only AR/AI smart glasses used
with the **Noa** app (`brilliant-noaflutter`, Flutter / `flutter_blue_plus`;
BLE logic recovered from `libapp.so` via Blutter). The app discovers Frame
purely by **advertised service UUID** — no manufacturer data, no name filter.

> Not to be confused with **Brilliant Home Technology** (SIG CID `0x0820`,
> smart-home switches) — an unrelated company.

## BLE Advertisement Format

### Identification

| Signal | Value | Mode / Notes |
|--------|-------|-------|
| Service UUID (128-bit) | `7a230001-5475-a6a4-654c-8431f6ad49c4` | Normal / connectable — the app's `startScan(withServices: …)` key |
| Service UUID (16-bit) | `0xFE59` (Nordic Secure DFU) | Frame in DFU / bootloader mode — generic Nordic, see [nordic-dfu.md](nordic-dfu.md) |
| Local name | `Frame` | Advertised by the open-source firmware; soft secondary signal only (the app doesn't filter on it) |
| Company ID | *(none)* | No manufacturer data parsed/required |

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| Frame glasses present (normal mode) | `7a230001-…` |
| Possibly a Frame in DFU mode | `0xFE59` + name `Frame` (FE59 alone is any Nordic device) |

No byte-level decode is possible or needed.

## What Requires GATT Connection

Everything functional (camera/mic/display/Lua) — see
`reports/brilliant-noaflutter.md`.

## Identity Hashing

```
identifier = SHA256("brilliant_frame:" + mac)[:16]
```

## Detection Significance

Camera-equipped smart glasses nearby — the same "recording-capable wearable"
privacy concern as other camera glasses. `7a230001-…` is vendor-specific and
a strong tell.

## adwatch Status

No plugin. Future plugin: match service UUID `7a230001-5475-a6a4-654c-8431f6ad49c4`
(and `0xFE59` only when the name is `Frame`).

## References

- apk-ble-hunting `reports/brilliant-noaflutter_passive.md` (Stage 6d Blutter recovery; `reports/brilliant-noaflutter.md`)
- Code cited: `asm/noa/bluetooth.dart` `BrilliantBluetooth::scan`
