# Google Find My Device network (FMDN) beacon frames — FEAA 0x40 / 0x41

## Overview

**Find My Device network** is Google's crowd-sourced locating network for
Android: trackers, earbuds and other accessories broadcast a rotating
ephemeral identifier, nearby Android phones report it (encrypted) to
Google, and the owner's Find My Device app resolves it. It is specified as
an extension of Fast Pair ("Find My Device Network accessory
specification") and its beacon advertisement **reuses the Eddystone service
UUID `0xFEAA`** with frame types Eddystone never defined:

| Frame type | Meaning |
|------------|---------|
| `0x40` | normal operation |
| `0x41` | **unwanted-tracking-protection mode** — the accessory believes it has been separated from its owner |

The rest of the service data is the ephemeral identifier (EID) — 20 bytes
on the 160-bit SECP160R1 curve (legacy BLE 4 advertising) or 32 bytes on
the 256-bit SECP256R1 curve (BLE 5 extended advertising) — optionally
followed by one **hashed flags** byte.

This matters to a passive scanner for two reasons. First, coverage: the
NearSight corpus holds 53 FEAA `0x40`/`0x41` records from 52 units
(2026-06-03 → 2026-08-30), several co-advertised with a Fast Pair `0xFE2C`
frame by earbuds. Until the 2026-09-02 sweep the `eddystone` parser claimed
the `0x40` frames as "Eddystone-EID" and read tx_power + an 8-byte EID out
of them — a mis-decode — and never claimed `0x41` at all. Second, meaning:
a `0x41` frame is the same "separated from owner" state Android's own
unknown-tracker alerts key on.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFEAA` | SIG-assigned to Google LLC; shared with Eddystone |
| Frame type | byte 0 = `0x40` / `0x41` | Eddystone uses `0x00` / `0x10` / `0x20` / `0x30` |
| EID | 20 or 32 bytes at [1..) | Rotates on the accessory's schedule; unlinkable across rotations without the owner's key |
| Hashed flags | optional last byte | Bits 5–6 battery level, bit 7 unwanted-tracking mode — XORed with the low byte of SHA-256(r), so opaque to a passive observer |
| Length | 21 / 22 (20-byte EID ± flags), 33 / 34 (32-byte EID ± flags) | Corpus: 22 records of 21 bytes, 31 of 22 bytes; no 32-byte EIDs seen yet |
| Device class | `tracker` | |

## Ad Format

```
41 | 20 9e 4c 97 76 e4 d5 4c 3c bd ef 3b 26 2b 06 6f c9 ea 5c 59 | 3c
type 20-byte EID                                                   hashed flags
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0 | frame type | `0x40` on 46 corpus records, `0x41` on 7 (spec) |
| 1..21 (or 1..33) | ephemeral identifier | 20 bytes on every corpus record (spec: 20 for SECP160R1, 32 for SECP256R1) |
| last (optional) | hashed flags | present on 31 of 53 records; the 21-byte records omit it |

### Captured examples

| Date (UTC) | Service data | Note |
|------------|--------------|------|
| 2026-08-30 17:27 | `41 209e4c9776e4d54c3cbdef3b262b066fc9ea5c59 3c` | −75 dBm, this sweep's pool record, UTP mode on |
| 2026-06-04 22:43 | `40 fcd0fcfa454ef78fba46da7ffc7750fd42a9822a dd` | 21 sightings |
| 2026-06-03 17:34 | `40 1ce212af515a3e474d9abfe7b9069ace0ff3c809` | 21 bytes, no flags |
| 2026-08-04 17:05 | `41 c9d73e0894a375ebeca3f4992fb940e849d87d6b 9d` + `FE2C 1042…` | Fast Pair earbuds (device type 66), 11 + 17 sightings |
| (JBL Endurance Peak 4) | `40 c0cd809892bd01932b304594281b4a24b982297a e1` | the capture `eddystone.md` used to present as an EID + "trailing bytes" |
| 2026-06-04 22:48 | `40 00…00 00` | all-zero EID, 20 sightings — an unprovisioned unit |

### Parser gate

`0xFEAA` service data whose first byte is `0x40` or `0x41` and whose length
is 21, 22, 33 or 34. Everything else on `0xFEAA` is Eddystone's
(`EddystoneParser` declines `0x40`/`0x41` in return, so exactly one parser
claims any FEAA frame).

## Identity Hashing

```
identifier = SHA256("google_fmdn:{eid_hex}")[:16]
stableKey  = "google_fmdn:{eid_hex}"          (eid tagged uniqueRotating)
all-zero EID: identifier = SHA256(ble_address)[:16], stableKey = nil
```

**Ephemeral by design.** The EID rotates every 2^K seconds (K = 10 by
default, about 17 minutes) and the accessory's BLE address rotates with it,
so the key is stable only within one rotation window — the same caveat as
Eddystone-EID. No corpus unit was seen across a rotation, which is exactly
what the design predicts. An all-zero EID falls back to the BLE address so
unrelated factory-state units do not collapse onto one key.

## What We Cannot Parse

- Who owns the accessory or what it is — the EID is an elliptic-curve
  point derived from a per-device key only the owner's phone holds
- Battery level and the UTP bit inside the hashed-flags byte (XOR-masked)
- The vendor: `0xFEAA` is Google's UUID, and the frame carries no vendor
  field. A co-advertised Fast Pair frame (`service_data_fast_pair_fe2c`)
  can sometimes identify the product through the Fast Pair model ID

## Detection Significance

A `0x40` frame means an accessory enrolled in Google's network is nearby.
A `0x41` frame means that accessory has decided it is **away from its
owner** — the state that makes it a candidate unwanted tracker, and the
condition under which the spec requires it to answer identifying reads
from any phone.

## Confidence / Attribution

**Protocol: high.** Frame types, EID lengths and the hashed-flags layout
come straight from Google's published specification, and every corpus
record fits it.

**Vendor / product: none claimed.** Google owns the UUID; the accessory
maker is unknown from this frame alone.

## References

- Google, "Find My Device Network accessory specification" — Fast Pair
  extensions, section "Advertisement":
  https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn
- `eddystone.md` — the Eddystone frames that share `0xFEAA`.
- NearSight `GoogleFMDNParser` (`Sources/Parsers/GoogleFMDNParser.swift`)
  and `research/sweep-2026-09-02-candidates.md`.
