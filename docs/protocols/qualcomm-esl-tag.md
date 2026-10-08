# Electronic Shelf Label Tag — Qualcomm FD05 Frame (ESL service 0x1857)

## Overview

A fleet of ~36 BLE tags captured in one 32-minute window (2026-08-15,
64 records / 417 sightings, −84..−102 dBm), every one advertising the
Bluetooth SIG **Electronic Shelf Label** service `0x1857` together with
an 18-byte service-data frame under Qualcomm Technologies' member UUID
`0xFD05`. The deployment shape — dozens of weak, one-day emitters, each
with a per-unit id and one of exactly two "group" values — is a store's
shelf-label fleet seen from an aisle, with two access points / ESL groups.

**Attribution stops at the chip vendor.** `0xFD05` tells us the BLE
silicon / stack is Qualcomm's; the label maker (VusionGroup/SES-imagotag,
Hanshow, SoluM, Pricer, …) is NOT identified and is not claimed. The
ESL *class* is claimed on the strength of the SIG service UUID: per the
ESL Profile an ESL advertises `0x1857` while unassociated or
unsynchronised with its AP, which is also the only state in which a
passive scanner would see a fleet of them at all.

## Identifiers

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `0x1857` | SIG *Electronic Shelf Label* service — **required** |
| Service UUID | `0xFD05` | Qualcomm Technologies, Inc. (SIG member UUID) |
| Service data key | `0xFD05` | 18-byte frame, first byte `0x06` — **required** |
| Manufacturer data | *(absent)* | |
| Local name | *(absent)* | |
| Address type | `random` | did NOT rotate within the capture |

## BLE Advertisement Format

### Service data under `0xFD05` (18 bytes)

```
06 c1 30 xx xx xx 26 ca a9 5a 5d 60 bc c7 gg gg gg gg
│  │  │  └──┬───┘ └─────────┬───────┘ └────┬────┘
│  │  seq  tag id        opaque (8)      group tag (4)
│  flags
frame type
```

| Offset | Size | Field | Evidence |
|---|---|---|---|
| 0 | 1 | frame type `0x06` | constant across all 64 records (gated) |
| 1 | 1 | flags | `c1` ×63, `c0` ×1 — reported raw |
| 2 | 1 | sequence | advances by exactly 1 per frame of a tag, roughly every 5 minutes |
| 3..5 | 3 | tag id | constant per tag; 36 distinct values |
| 6..13 | 8 | opaque | fresh on every sequence step, identical within a step (14 sightings of one payload) — a MIC / ciphertext |
| 14..17 | 4 | group tag | one of two values fleet-wide: `gggggggg` (20 tags), `hhhhhhhh` (16 tags) |

Real captures:

```
06c130xxxxxx26caa95a5d60bcc7gggggggg   38 sightings
06c131xxxxxxdac68e9139463f7fgggggggg   11 sightings — same tag, seq 0x30→0x31
06c1b9yyyyyy32352864c6b33e9dhhhhhhhh   14 sightings — other group
06c0d2zzzzzz530be0ce9dc04116hhhhhhhh    1 sighting  — flags 0xc0
```

One tag's five frames, with CoreBluetooth reporting the same peripheral
identifier throughout (the address held while the payload changed):

```
03:04  06c1 b7 yyyyyy 42fb5e5fa3354bee hhhhhhhh
03:09  06c1 b8 yyyyyy 734f1b3ce3e331b2 hhhhhhhh
03:10  06c1 b9 yyyyyy 32352864c6b33e9d hhhhhhhh
03:20  06c1 ba yyyyyy 4cbeef200b1ed443 hhhhhhhh
03:26  06c1 bb yyyyyy 1f8c6ef322f69b4f hhhhhhhh
```

### Alternative reading (recorded, not adopted)

Bytes 2..5 could be a single little-endian 32-bit counter whose low byte
was all that moved in a 32-minute capture. The values (the 3-byte tag id plus the sequence
byte, read as one LE word) are not plausible uptimes or Unix times, which is why
the `[seq][3-byte id]` reading was adopted — but if the counter reading
is right, the "tag id" changes every 256 ticks (~21 h at 5 min/tick) and
the stable key with it. A multi-day capture of one tag settles this.

### Other FD05 frames (not this device)

- 19-byte static config frame `05e001e8036400f401c8000200000100010000`
  (2026-07-31 sweep, 28 records, one emitter) — different type byte and
  length; rejected by the gate.
- 3-byte `030010` advertised with `0x18CF` + `0xFD05` — rejected.

## Parser Scope (Passive Only)

Surfaces: `frame_type`, `flags_hex`, `sequence`, `tag_id_hex`,
`opaque_hex`, `group_tag_hex`, `esl_service_advertised`. Identity keys on
the payload, not the address:

```
stable_key = qualcomm_esl_tag:<group tag hex>:<tag id hex>
identifier = SHA256(stable_key)[:16]
```

Not decoded: what the 8-byte field protects, what the group tag indexes
(AP id / ESL group id / network key id), label size, displayed price, or
the label vendor.

## Detection Significance

A burst of these is a retail floor (supermarket, pharmacy, electronics)
using Bluetooth-standard ESLs — or a back room / pallet of unprovisioned
ones. Individually they are fixed infrastructure and of no tracking
interest; the stable per-tag id is expected (the store needs it).

## Confidence

- Structure: HIGH (64 records, 36 tags, consistent byte roles).
- "Electronic shelf label": HIGH (SIG service UUID is unambiguous).
- Qualcomm silicon: HIGH (SIG member UUID).
- Label brand: NONE claimed.

## References

- [BT SIG `service_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/service_uuids.yaml) — `0x1857 = Electronic Shelf Label`
- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFD05 = Qualcomm Technologies, Inc.`
- Bluetooth SIG, *Electronic Shelf Label Profile 1.0* (2023) — advertising
  requirements in the Unassociated / Unsynchronized states
- NearSight `research/sweep-2026-08-23-candidates.md` — cluster analysis
