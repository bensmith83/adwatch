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
parser.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `42594420-4155-544F-E0A9-E50E24DCCA9E` | 128-bit exact match ≈ zero false positives; first 8 bytes = "BYD AUTO" |
| Manufacturer data | 6 bytes, optional | the car's BLE random static address (below) |

### Manufacturer data: a random static address

The 6 bytes are a BLE **random static address**, most significant byte
first: `ss:xx:xx:xx:xx:xx`, where the top two bits of the first byte are
`0b11`. Every blob seen from 2026-09-29 to 10-12 (18 distinct values) has
those bits set, which uniform random bytes would do once in 4^18. In the
NearSight 2026-10-18 export each value also spans several CoreBluetooth
device identifiers within seconds, so it outlives the rotating advertising
address.

The field's first two bytes only look like a company ID because
manufacturer data is read that way: with a first byte of `0xC0`–`0xFF`
they spell an arbitrary "CID" (for example `0x2BC3`, `0xF2EE`, or
`0x00C4`, LG Electronics' real slot). Nothing in it is a vendor claim, so
a scanner must not route this frame to company-ID parsers. NearSight's
registry gives this UUID an *exclusive* route for that reason.

```
Offset  Field
------  -----
 0–5     random static address, MSB first (byte 0 top bits 0b11)
```

## Parser Scope (Passive Only)

`BydAutoBeaconParser` (`byd_auto_beacon`, deviceClass `vehicle`):

- Gates on the exact 128-bit service UUID. The manufacturer data is
  surfaced when present but never required (some records carry none).
- Emits `service_uuid_ascii` ("BYD AUTO"), `blob_hex`, and, when the
  top-bits check holds, `embedded_address` (colon form) with
  `embedded_address_type` `random_static`.
- Identity = the address when present (survives BLE address rotation until
  the car re-mints it); else the BLE address.

## Attribution Confidence

**Vendor: high** — "BYD AUTO" is embedded verbatim in a custom UUID, the
same self-labelling evidence class as the shipped Jieli "ZHJIELI"
pseudo-CID parser. **Identity: per-unit, rotating** — a random static
address is fixed for a power cycle but may be re-minted at the next one
(Core Spec Vol 6 Part B §1.3.2.1). One value persisted three days
(2026-09-30 → 10-02); others appeared on a single day each. So it is
tagged `.uniqueRotating`, not `.uniqueStable`. **Product line: unpinned.**

## References

- NearSight app research write-up `research/sweep-2026-10-17-candidates.md`
- Bead nearsight-d277 (the 2026-10-05 analysis) and nearsight-jub2 (the
  address finding)
- [BYD Auto (Wikipedia)](https://en.wikipedia.org/wiki/BYD_Auto)
