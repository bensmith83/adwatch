# DJI Ronin / RS-Series Gimbal Plugin

## Overview

DJI's handheld stabilizer line — Ronin, RS, RSC, Osmo Mobile — pairs with the **DJI Ronin** smartphone app over BLE to configure shooting profiles, run motor calibration, trigger camera control, and apply firmware updates. Each unit advertises continuously while powered on so the app can re-attach automatically.

This parser surfaces the gimbal's product line, model variant, and unit serial — all of which are encoded in the BLE `local_name`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `^DJI ` | E.g. `"DJI RS3 MINI-060WDX"`, `"DJI Osmo Mobile 6-XYZ"`. |
| Service UUID | `0x1812` (HID over GATT) | Lets the gimbal act as a Bluetooth camera-remote / keyboard. |
| Service UUID | `0xFFF0` | DJI's vendor-allocated 16-bit service. |
| Company ID | `0x08AA` (when manufacturer data is present) | SIG registry: "Zhuhai Hoksi Technology CO.,LTD" — DJI's OEM partner / SIG registration alias rather than DJI's own ID. |

### Local Name Format

`DJI <product line>[ <variant>]-<unit serial>`

- `"DJI RS3 MINI-060WDX"` → product `RS3 MINI`, serial `060WDX`.
- `"DJI RS 3 Pro-XYZ123"` → product `RS 3 Pro`, serial `XYZ123`.
- `"DJI Osmo Mobile 6-ABC"` → product `Osmo Mobile 6`, serial `ABC`.

The serial after the dash is alphanumeric, varies in length, and is the unit's permanent ID.

### Manufacturer Data (when present)

11 bytes after the `aa 08` company-ID prefix. Bytes appear to encode a session/pairing nonce; we surface the raw payload as `payload_hex` but the per-byte semantics are not validated.

## Detection Significance

- **Film sets, content creators, weddings.** A DJI Ronin in the wild is a strong signal of professional or prosumer video production nearby.
- **Stable serial enables tracking.** The local-name serial persists across MAC rotations.

## What We Cannot Parse from Advertisements

- Gimbal mode (balanced / follow / FPV) — read via the GATT connection to the Ronin app.
- Battery level, motor calibration state, camera-control profile — same.

## References

- [DJI RS 3 Mini product page](https://www.dji.com/rs-3-mini)
- [DJI Ronin app (iOS)](https://apps.apple.com/us/app/dji-ronin/id1481405257)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
