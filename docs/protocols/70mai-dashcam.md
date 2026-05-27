# 70mai Dashcam Plugin

## Overview

[70mai](https://70mai.com/) (Shanghai 70mai Co., Ltd., founded 2016, Xiaomi-invested but operationally independent) makes consumer-grade in-car dash cameras. Their mid- and high-tier models (A-series `A810` / `A810 Plus`, M-series `M500` / `M800`, `T800`, `Omni X800`, etc.) carry both Wi-Fi and BLE radios. BLE is used as a discovery / pairing-bootstrap channel for the 70mai companion app; the app then hands off to Wi-Fi for video pull and recording configuration. Entry-level units (A800S, older M-series) are Wi-Fi-only.

This parser surfaces the dashcam model (`A810 Plus`, `M500`, `Omni X800`, …) and its stable 4-hex serial suffix from the BLE local name. There is no manufacturer-specific data and no custom service UUID — identification is purely name-prefix based.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `^70mai_.+_[0-9A-Fa-f]{4}$` |
| Company ID | _absent_ — 70mai does not hold a SIG company ID. |
| Service UUIDs | _none observed_ — connection-time only. |

### Local Name Format

`70mai_<MODEL>_<4-hex serial>`

- `<MODEL>` is the marketing model token from the device label — may contain internal whitespace (`A810 Plus`, `Omni X800`, `Pro Plus+`). The regex captures the model greedily.
- `<4-hex serial>` is the last two bytes of the dashcam's MAC address, displayed in lowercase on the unit label, and is the same suffix used by the Wi-Fi SSID (the 70mai M500 user manual documents `70mai_M500_XXXX` as the Wi-Fi SSID format). Stable per unit — usable as a fingerprint anchor.

Examples:
- `"70mai_A810 Plus_5bc1"` → model `A810 Plus`, serial `5bc1`
- `"70mai_M500_a1b2"` → model `M500`, serial `a1b2`

## Detection Significance

- **Stable serial.** The 4-hex suffix doesn't rotate and is the same value used to brand the Wi-Fi SSID and printed on the physical device label. It's effectively a deterministic per-cam identifier.
- **Cars in parking lots / drive-throughs.** A dense cluster of 70mai advertisements is a strong signal you're scanning near roads or in parking facilities — every powered 70mai-equipped vehicle in earshot will broadcast.

## What We Cannot Parse from Advertisements

- Recording state, parking mode, GPS/G-sensor state — all post-connect over Wi-Fi (the 70mai app uses HTTP over the cam's Wi-Fi AP).
- Firmware version / encryption status — Wi-Fi side only.

## References

- [70mai product line](https://dashcam.70mai.com/dashcams/)
- [70mai M500 user manual (PDF — SSID format)](https://object.pscloud.io/cms/cms/Uploads/file_0_427_166_0_0.pdf)
- [alu.dog: Reverse engineering the 70mai Android app](https://alu.dog/posts/reverse-engineering-the-70mai-android-app/) — Wi-Fi/HTTP side, no BLE.
- [DashCamTalk Omni X800 thread (confirms 4-hex serial on label)](https://dashcamtalk.com/forum/threads/unable-to-connect-to-70mai-omni-x800-4k-via-bluetooth-or-wi-fi.53252/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — 70mai not assigned.
