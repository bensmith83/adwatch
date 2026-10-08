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

Initial capture (5 adwatch exports, 7 distinct devices, 33 sightings):
`serviceData = {"FE50": "fbf3"}` — exactly 2 bytes, always `fbf3` — with
no `serviceUUIDs`, no manufacturer data, no local name,
`addressType = random`, RSSI consistently far (−100 to −97).

**v1.1 correction (2026-10-08 sweep, bead nearsight-s0hf):** the
"constant `fbf3` = frame-type magic" reading of that small sample is
refuted by the full-history corpus: **36 records / 335 sightings / 12
capture days (2026-07-10 → 2026-10-02) with 22+ distinct 2-byte values
and none of them `fbf3`** — most-seen `c8 0d` (118 sightings across 5
same-day records), then `6c 38`, `7a d9`, `a4 36` (31), `03 19` (25),
`b8 eb`, `5f 35` … The 2 bytes are a **per-device/per-epoch token**, not
a frame magic. One value can recur across several receivers of a single
emitter (the 5 same-day `c80d` records), so the token is not unit
identity either. The parser gate is therefore **any exactly-2-byte
payload**; length stays part of the gate because no 1-byte or ≥3-byte
FE50 frame has ever been observed (a different length would indicate a
different beacon subtype this parser must not misattribute).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service-data key | `0xFE50` | Google LLC — SIG-registered |
| Service-data payload | any 2 bytes | per-device/per-epoch token (22+ distinct values observed) |
| Service UUIDs | *(absent in observed captures)* | |
| Manufacturer data | *(absent)* | |
| Local name | *(absent)* | |
| Address type | `random` | |

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `Google LLC` |
| `sig_service_uuid` | hard-coded | `0xfe50` |
| `token_hex` | service-data | the 2-byte token, echoed raw |
| `candidates` | hard-coded | "Chromecast / Nest family / legacy Google accessory (unconfirmed)" |

### What We Cannot Surface from the Advertisement

- Specific Google product (Chromecast vs Nest Hub vs Nest Mini vs …).
- Live device state (cast session active, audio playing, etc.).
- Account / household pairing.
- Anything beyond "a Google accessory is in range and emitting the
  FE50 2-byte beacon."

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

- ~~Capture FE50 frames with different payloads~~ — **done**: the
  162k-record corpus shows the payload is a per-device/per-epoch token
  (see "v1.1 correction" above); the gate widened to any 2-byte value in
  parser v1.1 (2026-10-08 sweep, bead nearsight-s0hf). Token semantics
  (lifetime, rotation epoch, emitter product) remain undecoded.
- Connect to a captured device's GATT 0x180A (Device Information
  Service) to read Manufacturer Name (0x2A29) and Model Number
  (0x2A24) — that would resolve the Chromecast/Nest/other guess.

## References

- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFE50` → Google LLC
- [Blatann BT SIG UUID DB](https://blatann.readthedocs.io/en/latest/blatann.bt_sig.uuids.html) — cross-confirmation
- [Nordic `bluetooth-numbers-database`](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — negative evidence (FE50 absent)
- [Google Nearby / Fast Pair docs](https://developers.google.com/nearby/fast-pair/specifications/introduction) — context (FE2C is the documented adjacent UUID)
