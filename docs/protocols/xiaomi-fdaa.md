# Xiaomi FDAA Name-Broadcast Plugin

## Overview

**Service UUID `0xFDAA`** is officially assigned to **Xiaomi Inc.** in the Bluetooth SIG's 16-bit member UUID registry (see *Assigned Numbers*, `member_uuids.yaml`). Xiaomi hold a small block of consecutive member UUIDs — `FDAA`, `FDAB`, `FE95` (MiBeacon), `FE9C`, `FE98` — each used for a different cross-device protocol.

FDAA is **not** MiBeacon (that's `FE95`, the encrypted sensor / Mi Band protocol decoded elsewhere in this codebase by `MiBeaconParser.swift`). FDAA is the frame Xiaomi phones (Mi / Redmi / POCO families) and some Xiaomi-ecosystem accessories broadcast while in **Mi Connect / HyperConnect** cross-device pairing-discoverable mode. The frame carries the device's human-readable **model name** as plain ASCII so that nearby Xiaomi devices can present it in the Mi Connect pairing UI ("Found: *Xiaomi 14T Pro*").

Four distinct units captured in the field (`research/adwatch_export 6.json`) all advertise the identical 19-byte service-data payload for the same model, which matches the expectation that the broadcast carries only the model identity — not a per-device anchor.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (16-bit) | `0xFDAA` — SIG-assigned to **Xiaomi Inc.** |
| Service data | Present, ≥ 3 bytes |
| Manufacturer data | Often present but model-specific; not anchored on for this parser |
| Local name | Typically absent — model name lives inside the FDAA service data |

### Service Data Layout

Observed Xiaomi 14T Pro frame (19 bytes total):

```
83 0c e3 58 69 61 6f 6d 69 20 31 34 54 20 50 72 6f
── header ── ── ASCII "Xiaomi 14T Pro" ──────────

Byte 0     : 0x83                    ← frame-type tag (constant across captures)
Bytes 1..2 : 0c e3                   ← opaque header (likely product-id /
                                       version / length — see "Uncertainty"
                                       below); surfaced as `header_hex`
Bytes 3..n : ASCII model name        ← `device_name` if every byte is
                                       printable ASCII (0x20..0x7E);
                                       otherwise we skip name extraction
                                       and surface `payload_hex` only.
```

### Uncertainty about the `83 0c e3` header

The byte-0 frame tag `0x83` is empirically constant across all four captured units and is the natural anchor for a frame-type. Bytes 1..2 (`0c e3` in the 14T Pro sample) are not documented in any public reverse-engineering write-up that I could locate (theengs/decoder, Bluetooth-Devices/xiaomi-ble, ESPHome `xiaomi_ble`, ATC_MiThermometer, and Xiaomi MIIO SDK references all cover MiBeacon `FE95`, not FDAA). They most plausibly encode some combination of product-id / hardware-version / payload-length, but until captures from other Xiaomi models accumulate we surface them as `header_hex` rather than guessing.

### Stable Key

We use `xiaomi_fdaa:<macAddress>`. **The broadcast contains no per-unit anchor** — every Xiaomi 14T Pro on the planet sends the same `83 0c e3 …` service data — so the only available device-scoped key is the BD_ADDR itself. Random-address rotation will fragment this; downstream identity inference would need to fall back on co-located manufacturer-data fingerprints.

## Detection Significance

- **Identifies a Xiaomi / Redmi / POCO phone (or Xiaomi-ecosystem device) currently in cross-device pairing-discoverable mode.** Phones don't sit in this mode continuously — it's surfaced when the user opens the Mi Connect / HyperConnect picker, the Quick Share sheet, or certain initial-pairing flows. A sighting therefore correlates with a Xiaomi user actively interacting with the cross-device UI.
- **Useful as a contact / proximity indicator.** Pair an FDAA sighting with a known Xiaomi-user fingerprint elsewhere in the home and you have stronger evidence of which Xiaomi device is which.
- **Model fingerprinting.** `device_name` is a strong device-model anchor (e.g. distinguishes a Xiaomi 14T Pro from a Redmi Note 13) without needing GATT.

## What We Cannot Parse from FDAA

- **Battery / sensor state.** FDAA is a pairing-announce frame, not a telemetry frame. There is no battery, HR, temperature, or step-count field.
- **Per-device serial / IMEI / account binding.** Anything that would identify *which* Xiaomi 14T Pro this is. Xiaomi keeps that on the encrypted GATT side of the pairing handshake.
- **Header field semantics.** Bytes 1..2 are surfaced as `header_hex` only — see "Uncertainty" above.

## References

- [Bluetooth SIG Assigned Numbers — 16-bit Member UUIDs (YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFDAA` is assigned to "Xiaomi Inc." (alongside `0xFDAB`, `0xFE95`, etc.).
- [Bluetooth SIG Assigned Numbers index](https://www.bluetooth.com/specifications/assigned-numbers/) — top-level entry point.
- [Xiaomi HyperConnect overview (Mi.com)](https://www.mi.com/global/discover/article?id=4829) — cross-device pairing framework that drives the FDAA discoverable-mode broadcast.
- [Bluetooth-Devices / xiaomi-ble (Python parser)](https://github.com/Bluetooth-Devices/xiaomi-ble) — covers MiBeacon (`FE95`) only; documents the gap that FDAA is **not** the same protocol.
- [Reverse engineering the MiBeacon protocol — Passive BLE Monitor](https://home-is-where-you-hang-your-hack.github.io/ble_monitor/MiBeacon_protocol) — comprehensive `FE95` reference; FDAA is explicitly out of scope.
