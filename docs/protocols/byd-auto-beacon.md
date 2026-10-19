# BYD Auto Vehicle Beacon (vanity UUID "BYD AUTO")

## Overview

Six nameless records / 13 sightings in the 2026-10-17 sweep advertise the
custom 128-bit service UUID `42594420-4155-544F-E0A9-E50E24DCCA9E`, whose
first eight bytes decode to ASCII **"BYD AUTO"** (`42 59 44 20 41 55 54
4F`) followed by eight non-ASCII bytes. BYD Auto is the automotive arm of
BYD (the Chinese EV and battery maker); a "BYD AUTO" vanity UUID on a
nameless, random-address device reads as the vehicle's **phone-as-key /
accessory BLE beacon** — the same passive class as GM PEPS, CCC digital
key, Tesla and Rivian. The specific product line (vehicle model, key
role) is not pinned from the advertisement.

The 2026-10-05 sweep first catalogued the family at 27 records / ~390
sightings / 2026-09-29 → 10-02 (bead nearsight-d277) and named the
parser; it deferred only on the blob-stability question, resolved here
by tagging the blob `.uniqueRotating`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `42594420-4155-544F-E0A9-E50E24DCCA9E` | 128-bit exact match ≈ zero false positives; first 8 bytes = "BYD AUTO" |
| Manufacturer blob | 6 bytes, optional | per-unit identity |
| Blob [0..2) | unassigned pseudo-CID (`0x2BC3`, `0x7FC3`, `0xF2EE`, `0x41E0`, …) | not a real SIG assignment |

### Byte Layout (6-byte blob, when present)

```
Offset  Field
------  -----
 0–1     leading two bytes — read LE as an unassigned pseudo-CID
 2–5     trailing four bytes — per-unit, surfaced raw
```

The whole 6 bytes are treated as one per-unit identifier (`blob_hex`);
the "pseudo-CID" is an artifact of reading the first two bytes as a
company identifier, not a real vendor claim.

## Parser Scope (Passive Only)

`BydAutoBeaconParser` (`byd_auto_beacon`, deviceClass `vehicle`):

- Gates on the exact 128-bit service UUID. The manufacturer blob is
  surfaced when present but never required (some records carry none).
- Emits `service_uuid_ascii` ("BYD AUTO"), the unassigned pseudo-CID
  (`company_id_hex`), and `blob_hex`.
- Identity = the blob when present (payload-derived, survives BLE
  address rotation within its re-mint window); else the BLE address.

## Attribution Confidence

**Vendor: high** — "BYD AUTO" is embedded verbatim in a custom UUID, the
same self-labelling evidence class as the shipped Jieli "ZHJIELI"
pseudo-CID parser. **Blob stability: unproven** — one blob persisted
three days (2026-09-30 → 10-02) while others appeared on a single day
each, so the blob is tagged `.uniqueRotating`, never `.uniqueStable`.
**Product line: unpinned.**

## References

- NearSight app research write-up `research/sweep-2026-10-17-candidates.md`
- Bead nearsight-d277 — the 2026-10-05 analysis this closes out
- [BYD Auto (Wikipedia)](https://en.wikipedia.org/wiki/BYD_Auto)
