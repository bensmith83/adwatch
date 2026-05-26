# SimpliSafe (Home Security)

## Overview

SimpliSafe ships a connected home-security ecosystem (base station,
keypad, sensors, smart lock, indoor/outdoor cameras, video
doorbell). Several of its products broadcast BLE while powered
— our captures show two distinct SKU families on the same vendor
CID.

The advertisements are identification-only. SimpliSafe's BLE
protocol is not publicly reverse-engineered (community work has
focused on the sub-GHz 433/315 MHz sensor protocol and the cloud
REST API); the BLE channel is used for onboarding and
out-of-Wi-Fi control via the SimpliSafe app. We surface
vendor + SKU family + per-unit ID; dynamic state (alarm armed,
sensor open/close, lock position, camera state) requires either
a paired GATT session or the SimpliSafe cloud.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x06B1` | "SimpliSafe, Inc." per SIG yaml — high-confidence vendor anchor |
| Service UUID (SS-series) | `26526EEA-C96A-45D0-854E-3BB05C450B56` | Custom 128-bit; newer SKUs |
| Service UUID (legacy) | `0x00CC` | Vendor-claimed 16-bit (not SIG-allocated); older SKUs |

The CID alone is sufficient to claim vendor; UUID + name pattern
further classifies SKU family.

## SKU Families

### SS-series (newer)

- Local name: `SS<8 hex>` (e.g. `SS010a2f57`)
- Service UUID: `26526EEA-C96A-45D0-854E-3BB05C450B56`
- Manufacturer data: `b1 06 | <unit-id 4 bytes> | <4 opaque bytes>`
  - The unit-id bytes literally equal the hex in the name suffix
    — sanity-check by parsing both sides and confirming equality
    (`unit_id_matches_mfg = true` in the captured example).

```
b1 06 | 01 0a 2f 57 | 95 2c f0 95
└──┬─┘ └─────┬────┘ └─────┬─────┘
   │         │            └── opaque (counter / state, unverified)
   │         └── unit id (matches local-name suffix)
   └── SimpliSafe CID (LE)
```

### Legacy SKU

- Local name: `<8 hex>` (e.g. `3982e7d7`)
- Service UUID: `0x00CC` (vendor-claimed short UUID — not SIG-assigned)
- Manufacturer data: `b1 06 | <8 opaque bytes>`
  - Bytes 2–5 do NOT equal the local-name hex on this SKU (`unit_id_matches_mfg = false`).
    Likely a mix of unit-id + rolling-counter / state, but unverified
    without more captures.

```
b1 06 | 86 6a 53 9b d4 c8 a9 87
└──┬─┘ └─────────┬─────────────┘
   │             └── opaque 8 bytes (unverified)
   └── SimpliSafe CID (LE)
```

## Product-Specific Classification

We cannot determine specific SimpliSafe product (base station,
keypad, smart lock, camera, doorbell) from the advertisement —
no public protocol documentation exists that maps SKU family or
UUID to a product line. If you need product-level granularity,
correlate the unit-id with the SimpliSafe account/app on a known
test setup.

## Identity Hashing

```
identifier_hash = SHA256(unit_id)[:16]      # preferred — stable per unit
identifier_hash = SHA256(mac_address)[:16]  # fallback when no name parses
```

Unit id is the 8-hex tail of the local name (with or without the
`SS` prefix). It survives BLE MAC rotation and is the right key
for cross-session identity on a stationary security device.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID `0x06B1` | SimpliSafe (high confidence) |
| SKU family | name pattern + UUID | SS-series vs. legacy |
| Unit id | local-name 8-hex tail | Stable per unit |
| Payload hex | mfg-data body | Surfaced verbatim for future decoding |

## What Requires GATT or Cloud

- Alarm armed/disarmed/triggered state
- Per-sensor open/close, motion-trip events
- Smart-lock position
- Camera state (recording, motion-trip)
- Doorbell ring events
- Battery levels on individual sensors
- Wi-Fi onboarding (initial pair)

The base station also speaks a separate sub-GHz protocol to its
own sensors (433/315 MHz, reverse-engineered in
`bggardner/simplisafe-rf`); BLE is a separate channel and
that work doesn't help with the BLE side.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x06B1` →
  "SimpliSafe, Inc." (definitive)
- Bluetooth SIG `service_uuids.yaml` / `member_uuids.yaml` —
  `0x00CC` is **not** SIG-assigned (vendor-claimed by SimpliSafe)
- Tenable TechBlog "Inside SimpliSafe Alarm System" — notes the
  base-station ESP32 exposes undocumented BLE; no protocol detail
- `bggardner/simplisafe-rf` — sub-GHz protocol RE (BLE not in
  scope)
- `bachya/simplisafe-python` — cloud REST API (BLE not in scope)
