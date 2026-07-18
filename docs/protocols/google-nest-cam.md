# Google Nest Cam (2nd gen) — `0xBB44` Pseudo-CID

## Overview

This protocol covers the **2nd-gen Google Nest Cam** family — Nest Cam
(battery), Nest Cam (wired) and the Nest Doorbell siblings released
since 2021 under the post-acquisition Google/Nest brand. These devices
advertise a fingerprint **distinct from the older `0xFEAF` Nest Labs
service-data frame** that `NestParser` already handles. The Cam family
emits a frame keyed on:

- **Pseudo-company-ID `0xBB44`** in the manufacturer-data prefix
  (`44 BB` LE). The slot is **not** registered with the Bluetooth SIG
  (Google's registered CID is `0x00E0`; Nest Labs' is `0x01B5`). Google
  squats `0xBB44` so that the first 3 mfg-data bytes (`44 BB 3B`)
  literally spell the **Google OUI 44:BB:3B** (registered to Google
  Inc. in 2020).
- A **Google-proprietary 128-bit service UUID**
  `D2D3F8EF-9C99-4D9C-A2B3-91C85D44326C` whose trailing `…44326C` echoes
  the same Google OUI bytes.
- Local name `"Nest Cam"` on most frames (alternating frames from the
  same physical device may drop the name).

## Supported Models

| Product | Notes |
|---------|-------|
| Nest Cam (battery) | 2nd gen, late-2021 release |
| Nest Cam (wired) | Indoor, 2nd gen |
| Nest Doorbell (battery / wired) | Same advertisement layout family observed in adjacent captures |

The parser does **not** attempt to distinguish the specific SKU from
the ad payload — the 4-byte rotating identifier (bytes 7..10) doesn't
encode product class in any way we've decoded.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Manufacturer-data CID | `0xBB44` | LE prefix `44 BB`; **unregistered** Google pseudo-CID |
| Mfg constant prefix | `44 BB 3B` | Spells the Google OUI in plaintext |
| Sub-frame marker | `0xDE` at offset 5 | constant fingerprint byte |
| Sub-frame subtype | `0x02` at offset 6 | constant fingerprint byte |
| Mfg payload length | exactly 11 bytes | hard length gate |
| Service UUID | `D2D3F8EF-9C99-4D9C-A2B3-91C85D44326C` | Google-proprietary, 128-bit |
| Local name | `Nest Cam` (or nil) | nil on alternating frames |
| Address type | `random` | privacy-rotating BD_ADDR |

### Payload Layout

```
[0..1] 44 BB   CID 0xBB44 LE
[2]    3B      frame_type — also byte 3 of the Google OUI 44:BB:3B
[3..4] XX XX   varies — possibly device-state / 16-bit counter
[5]    DE      sub-frame marker (constant)
[6]    02      sub-frame subtype / length (constant)
[7..10] XX XX XX XX   4-byte rotating identifier (rotates per BD_ADDR cycle)
```

### Match Rule (required)

CID `0xBB44` alone is **not enough** — the slot is unregistered, so any
squatter could collide. We require:

```
mfg[0..1] == 44 BB  AND  mfg[2] == 3B
AND mfg[5] in {DE, 82}  AND  mfg[6] == 02
AND mfg.count == 11
AND ( serviceUUID contains D2D3F8EF-…  OR  localName == "Nest Cam" )
```

(`0x82` added 2026-07-17 — see Corpus Notes below. A second frame family,
OUI `64:16:66`, is also matched; see Corpus Notes for its layout.)

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Google` |
| Product | hard-coded | `Nest Cam` |
| `frame_type_hex` | mfg[2] | currently always `3b` |
| `rotating_id_hex` | mfg[7..10] | 4-byte privacy-rotating identifier |
| `payload_hex` | mfg[2..] | full payload after CID |

### What We Cannot Parse from the Advertisement

- Specific product SKU (battery vs wired Cam vs Doorbell).
- Recording state, motion detection, person/pet/package events.
- Battery level, charging state.
- Subscription tier (Nest Aware presence).
- Firmware version, Wi-Fi connectivity to Google's cloud.

All live state lives behind the Google Home / Nest cloud APIs.

## Stable Identity

The 4-byte rotating identifier rotates per address-randomization cycle,
so it isn't a per-device stable key. Until we capture a long enough
window to identify a non-rotating field, we combine the rotating ID
with the current MAC:

```
stable_key = google_nest_cam:<mac>:<rotating_id_hex>
identifier = SHA256(stable_key)[:16]
```

This is intentionally rotation-aware: a single physical Nest Cam will
appear as multiple stable keys over time, matching the privacy intent
of Google's design. Cross-rotation deduplication would require
either listening long enough to see the BD_ADDR repeat or running
side-channel correlation on RSSI/timing — out of scope for the parser.

## Detection Significance

- A residential / commercial Google Nest Cam or Nest Doorbell is in
  range and actively broadcasting.
- Distinct from the older FEAF Nest devices (thermostats, Nest Mini,
  Hub, original-gen cams) — those are picked up by `NestParser`.
- Long dwell + multiple stable keys for the same MAC group hints at a
  mains-powered Cam (continuous BLE), while sparse / mobile sightings
  suggest a battery Cam in low-power mode.

## Corpus Notes

- **A second OUI frame family exists** (shipped in the 2026-07-06 sweep,
  never documented until now): OUI `64:16:66` — the IEEE-registered **Nest
  Labs Inc.** OUI (Google-owned), spelled the same way Frame A spells
  `44:BB:3B`. This frame's structural bytes `[3..10]` differ from Frame A
  and were seen on one device in one short window, so the parser
  fingerprints only the OUI + 11-byte length and **requires** the vendor
  UUID (a bare 3-byte OUI is a real IEEE prefix and could collide in a
  larger corpus; the 128-bit vendor UUID is airtight). Match rule:
  `mfg[0..2] == 64 16 66 AND mfg.count == 11 AND serviceUUID contains
  D2D3F8EF-…` (name-only is rejected — no OUI-alone shortcut for this
  variant).
- **Sub-frame marker `0x82` (2026-07-17 sweep).** Real telemetry surfaced
  a Frame-A capture (147 + 11 sightings, one physical device) carrying
  both the vendor UUID *and* the exact `"Nest Cam"` name — the two anchors
  the match rule already trusts — but with `mfg[5] = 0x82` instead of the
  only previously-observed `0xDE`. Since the vendor UUID/name anchor
  already rules out accidental OUI collisions, `0x82` is accepted as a
  second known sub-frame-marker value rather than treated as a structural
  mismatch. A marker value that is neither `0xDE` nor `0x82` is still
  rejected.

## References

- [maclookup.app — OUI 44:BB:3B = Google Inc. (2020-04-16)](https://maclookup.app/macaddress/44bb3b)
- [Bluetooth SIG assigned numbers — confirms 0xBB44 not assigned](https://www.bluetooth.com/specifications/assigned-numbers/) (Google = 0x00E0, Nest Labs = 0x01B5)
- [Google Store — Nest Cam (Battery), 2nd gen](https://store.google.com/product/nest_cam_battery)
- [Google support — Nest setup uses BLE provisioning](https://support.google.com/googlenest/answer/9293657)
