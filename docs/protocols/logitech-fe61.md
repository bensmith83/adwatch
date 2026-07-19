# Logitech FE61 Beacon

## Overview

`0xFE61` is a 16-bit service UUID allocated by the Bluetooth SIG to
**Logitech International SA**. A subset of Logitech's BLE-native
peripherals — most plausibly **Spotlight presentation remotes**, the
R500/R500s laser presentation remotes, Litra-family lights, Logi Dock,
and Tap IP — advertise the bare FE61 service UUID as a pairing /
"find-me" beacon while idle. Unifying and Bolt mice/keyboards use a
proprietary 2.4 GHz radio instead and do not broadcast FE61.

The captured device additionally prefixes its manufacturer-data
payload with company ID `0x0003` — which the BT SIG assigns to
**IBM Corp**, not Logitech. This is a documented Logitech firmware
spec violation that has been observed in the wild before; the parser
surfaces the violation in metadata.

The advertisement is identification + presence only; live HID events
(button presses, sensor data) run over the encrypted GATT link to the
paired host.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FE61` | Logitech International SA (BT SIG) |
| Company ID (mfr-data) | `0x0003` (observed) | IBM Corp per SIG — Logitech firmware misuse |
| Local name | (absent) | |

The parser matches on the FE61 service UUID alone. The manufacturer-
data block is optional — when present, it carries device-token bytes
and a trailing-MAC candidate that the parser surfaces.

## Wire Format

### Long-form payload (after CID stripped)

```
[device_token (13 B)] 12 00 [device_token (13 B)] [trailer_mac (6 B)] 12
```

| Offset (post-cid) | Bytes | Field |
|-------------------|-------|-------|
| 0–12              | 13    | `device_token` — opaque per-unit identifier |
| 13–14             | 2     | `12 00` — AD-length / type separator for the next AD struct |
| 15–27             | 13    | `device_token` repeated |
| 28–33             | 6     | `trailer_mac_candidate` — likely the device's static BD_ADDR echoed in payload |
| 34                | 1     | trailing byte (`12` observed; plausibly RSSI / tx-power) |

The `c0:28:8d` OUI of the trailer is a real IEEE OUI allocation, lending
credibility to the "echoed BD_ADDR" reading.

### Short-form payload

When the second copy of the token and the 6-byte trailer are absent:

```
[device_token (13 B)] 12
```

The parser exposes `device_token` whenever the payload is at least 13
bytes long; `trailer_mac_candidate` only appears when the full long
form is captured.

## Captured Examples

```
mfg = 03 00 00 00 30 63 00 00 02 28 c7 09 cb cb b7
            12 00 00 00 30 63 00 00 02 28 c7 09 cb cb b7
            c0 28 8d 5d 06 3a 12                          (64 sightings)

mfg = 03 00 00 00 30 63 00 00 02 28 c7 09 cb cb b7 12     (4 sightings)
```

Captured 2026-05-31 in `research/adwatch_export 14.json` — single
device, ~68 sightings.

## Identity Hashing

```
identifier_hash = SHA256("logitech_fe61:token:<device_token>")[:16]   # when token present
identifier_hash = SHA256("logitech_fe61:mac:<MAC>")[:16]              # fallback
```

The `device_token` is stable per physical unit across MAC rotations,
making it a reliable per-device identity when the long or short form
is captured. Bare-UUID broadcasts (no manufacturer data) fall back to
the current BD_ADDR.

## Spec-Violation Flag

When the manufacturer-data CID is `0x0003` (IBM), the parser sets
`metadata.spec_violation = "cid_0x0003_ibm"`. This is purely a
diagnostic field — the parser still produces a valid result. A future
firmware update from Logitech could correct the CID to `0x046D`
(Logitech's own SIG allocation), at which point the flag will be
absent.

## What We Cannot Parse Without GATT

- HID button / scroll / motion events
- Battery level
- Firmware version
- Paired-host identity / pairing state
- Specific product SKU (Spotlight vs. R500 vs. Litra vs. Logi Dock)

## References

- BT SIG member_uuids.yaml: `0xFE61 → Logitech International SA`
- BT SIG company_identifiers.yaml: `0x0003 → IBM Corp` (Logitech firmware misuse)
- [moonbase.lgbt — BLE Spec Violations (notes the exact FE61 + CIC 0x0003 anomaly)](https://moonbase.lgbt/blog/bluetooth-low-energy-spec-violations/)
- [Logitech Spotlight Presentation Remote](https://www.logitech.com/en-us/shop/p/spotlight-presentation-remote)
- [Logitech R500s Laser Presentation Remote](https://www.logitech.com/en-us/shop/p/r500s-laser-presentation-remote)
- [Solaar — Logitech device database](https://github.com/pwr-Solaar/Solaar)
