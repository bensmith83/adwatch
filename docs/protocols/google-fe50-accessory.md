# Google FE50 Accessory Beacon

## Overview

`0xFE50` is registered to **Google LLC** per BT SIG `member_uuids.yaml`,
but is **distinct from Google's better-known allocations**:

| Google UUID | Purpose | Parser |
|---|---|---|
| `0xFE2C` | Fast Pair | `FastPairParser` |
| `0xFEAA` | Eddystone (legacy) | `EddystoneParser` |
| `0xFE9F` | Find My Device | `GoogleFMDParser` |
| `0xFEF3` | Android Nearby | `GoogleAndroidNearbyParser` |
| `0xFCF1` | Play Services Nearby Presence | `GoogleFcf1Parser` / `GooglePlayServicesParser` |
| **`0xFE50`** | **(this parser)** — undocumented Google accessory beacon | `GoogleFE50AccessoryParser` |

FE50 has no public spec and is notably absent from Nordic's
`bluetooth-numbers-database` — suggesting it's used by an internal /
legacy Google framework rather than a public one. The parser captures
the fingerprint and surfaces vendor attribution without claiming
specific product identity.

## Observed Behavior

Captured across 5 adwatch exports, 7 distinct devices, 33 sightings:

- `serviceData = {"FE50": "fbf3"}` — exactly 2 bytes, **always `fbf3`**
- no `serviceUUIDs`, no manufacturer data, no local name
- `addressType = random`
- RSSI consistently far (−100 to −97)

The constant `fbf3` payload across all 7 devices is a frame-type /
version magic, not a per-device identifier (analogous to Eddystone's
leading frame-type byte). The parser gates strictly on `fbf3` so future
Google FE50 frames with different payloads (which would indicate a
different beacon subtype) won't be misattributed to this one.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service-data key | `0xFE50` | Google LLC — SIG-registered |
| Service-data payload | exactly `fb f3` (2 bytes) | frame-type / version magic |
| Service UUIDs | *(absent in observed captures)* | |
| Manufacturer data | *(absent)* | |
| Local name | *(absent)* | |
| Address type | `random` | |

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `Google LLC` |
| `sig_service_uuid` | hard-coded | `0xfe50` |
| `frame_magic_hex` | service-data | `fbf3` |
| `candidates` | hard-coded | "Chromecast / Nest family / legacy Google accessory (unconfirmed)" |

### What We Cannot Surface from the Advertisement

- Specific Google product (Chromecast vs Nest Hub vs Nest Mini vs …).
- Live device state (cast session active, audio playing, etc.).
- Account / household pairing.
- Anything beyond "a Google accessory is in range and emitting the
  FE50 fbf3 beacon."

## Stable Identity

No per-device payload bits → MAC-anchored stable key. Distinct devices
rotate to new MACs and appear as fresh identities — matches Google's
privacy-rotation pattern.

```
stable_key = google_fe50_accessory:<bd_addr>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- A Google ecosystem accessory in the Chromecast / Nest family is
  likely nearby. The far-RSSI dwell pattern fits a permanently
  installed device (Hub on a counter, Chromecast on a TV).
- Distinct beacon from FE9F (Find My Device) and FE2C (Fast Pair) —
  this is a passive accessory presence indicator, not a paired-device
  tracker.

## Future Work

- Capture FE50 frames with different payloads — if any exist, document
  the byte semantics and either add subtypes here or split into
  sibling parsers.
  - **Update (2026-07-17 sweep):** three non-`fbf3` payloads have now
    been observed — `5f35`, `3821`, `b8eb` — each on a confirmed-distinct
    physical device (via `deviceIdentifier`), each seen exactly once. No
    two devices share a value, so there isn't yet a repeated pattern to
    decode: each could be a distinct subtype magic, a per-device rotating
    token, or noise. `GoogleFE50AccessoryParser` correctly rejects all
    three (this is the "different payload" case this doc already
    predicted). Needs multiple independent sightings of the *same* value
    before any of the three is decodable enough to ship.
- Connect to a captured device's GATT 0x180A (Device Information
  Service) to read Manufacturer Name (0x2A29) and Model Number
  (0x2A24) — that would resolve the Chromecast/Nest/other guess.

## References

- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFE50` → Google LLC
- [Blatann BT SIG UUID DB](https://blatann.readthedocs.io/en/latest/blatann.bt_sig.uuids.html) — cross-confirmation
- [Nordic `bluetooth-numbers-database`](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — negative evidence (FE50 absent)
- [Google Nearby / Fast Pair docs](https://developers.google.com/nearby/fast-pair/specifications/introduction) — context (FE2C is the documented adjacent UUID)
