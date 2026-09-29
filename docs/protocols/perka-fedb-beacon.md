# Perka / Clover Rewards loyalty beacon (service UUID 0xFEDB, CID 0x0005)

## Overview

A merchant-side BLE beacon that advertises the Bluetooth SIG **member
UUID `0xFEDB`** — registered to **Perka, Inc.** — together with a fixed
14-byte manufacturer-data frame under company ID `0x0005`.

Perka was a mobile loyalty platform (2011) whose BLE "Perka Beacon" let a
merchant check customers in hands-free as they walked through the door,
with the Perka app running in the background on the customer's phone. First
Data distributed the beacons free to small merchants in 2014–15, and in 2018
Perka was rebranded into its sister company Clover (now Fiserv) as **Clover
Rewards**. Whether the units captured here are the original standalone
beacons or the BLE radio inside a Clover POS terminal is **not known** — the
closest capture sat at −54 dBm for 11 sightings, i.e. at a counter, which
fits either.

CID `0x0005` is SIG-registered to **3Com**, which has not existed since
2010 and never made BLE hardware. It is read as a firmware default /
placeholder; the attribution rests entirely on the member UUID.

Four distinct devices have been captured between 2026-07-13 and
2026-08-29 (41 records, ~470 sightings):

| First seen | Payload (after CID) | Records · sightings | Note |
|------------|---------------------|---------------------|------|
| 2026-07-13 | `00 01 0690 00000000 00 01 710e` | 2 · 288 | −59 dBm, one location |
| 2026-08-19 | `00 01 b0a9 00000000 00 02 1a52` | 22 · ~40 | seen 08-19 → 08-23, same location |
| 2026-08-19 | `00 02 1ba5 00000000 00 02 8497` | 9 · ~20 | same days and location as above |
| 2026-08-29 | `00 02 0f0b 00000000 00 02 7803` | 1 · 11 | −54 dBm |

NearSight rejected the family at n=1 (2026-07-17, "static blob"), put it on
the watchlist at n=2 (2026-08-23, trigger "3rd payload") and promoted it on
2026-08-30 when the third new payload appeared.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFEDB` | SIG member UUID → *Perka, Inc.* — the attribution |
| Company ID | `0x0005` (LE wire `05 00`) | SIG → *3Com*; placeholder, **not** a vendor claim |
| Payload | 12 bytes, constant per device | Two 4-byte fields around 4 zero bytes |
| Address type | random, rotates | Payload never changes across rotations |
| Local name | none | |
| Device class | `beacon` | |

## Ad Format — 14 bytes

```
offset  0  1 | 2  | 3  | 4  5  | 6  7  8  9  | 10 | 11 | 12 13
        05 00 | 00 | 02 | 0f 0b | 00 00 00 00 | 00 | 02 | 78 03
        CID     00   type  id      reserved      00   type  id
               └── field A ──┘                  └── field B ──┘
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0x0005` LE | 41/41 |
| 2 | `0x00` | 41/41 |
| 3 | field A type nibble, `0x01` or `0x02` | (1, 1, 2, 2) across the four devices |
| 4–5 | field A id, per device | `0690`, `b0a9`, `1ba5`, `0f0b` |
| 6–9 | reserved, all zero | 41/41 |
| 10 | `0x00` | 41/41 |
| 11 | field B type nibble, `0x01` or `0x02` | (1, 2, 2, 2) — **not** always `0x02`, so not gated |
| 12–13 | field B id, per device | `710e`, `1a52`, `8497`, `7803` |

No semantics are claimed for the type nibbles or the ids (merchant id /
beacon id / major-minor are all plausible readings; nothing in four devices
distinguishes them). The parser reports `field_a_hex` / `field_b_hex`, the
two type bytes, and `beacon_id` = field A ∥ field B.

### Parser gate

- service UUID `0xFEDB` present (short or 128-bit form), **and**
- company ID `0x0005`, **and**
- total length exactly 14, **and**
- byte 2, bytes [6..10) and byte 10 all zero.

A bare `05 00` CID (the shape Motive ELD units emit alongside `0xFC6D`) or a
`0x0005` frame without `0xFEDB` is never claimed.

## Identity Hashing

```
identifier = SHA256("perka_fedb_beacon:{field_a_hex}{field_b_hex}")[:16]
stableKey  = "perka_fedb_beacon:{field_a_hex}{field_b_hex}"
```

`beacon_id` is tagged `uniqueStable`. Every device rotated its random
address (up to 22 CoreBluetooth identifiers for one payload) while the
payload never changed, so the payload is the only usable anchor.

## What We Cannot Parse

- Which merchant / store the beacon belongs to (the ids are opaque)
- Whether the emitter is a standalone Perka Beacon or a Clover terminal
- Battery, firmware, or any per-sighting state — the frame is static

## Detection Significance

A sighting means **a merchant running Clover Rewards / Perka loyalty is
within BLE range** — a shop counter, café or restaurant. The beacon's
purpose is to let the Clover app on a customer's phone check them in
silently; from the scanner's side it is a fixed, re-identifiable fixture of
that venue.

## Confidence / Attribution

**Registrant: high.** `0xFEDB` is a SIG member UUID, which requires
membership to allocate, and it is registered to Perka, Inc.

**Product: medium.** "Loyalty check-in beacon" is what Perka's UUID would be
used for, and the −54/−59 dBm counter-side captures fit, but no named
capture or teardown confirms it.

**Field semantics: low.** Reported raw.

## References

- Bluetooth SIG `member_uuids.yaml` — `0xFEDB = Perka, Inc.`;
  `company_identifiers.yaml` — `0x0005 = 3Com`.
- Retail Dive, "Local merchants receive free beacons to boost Perka loyalty
  program" (First Data beacon rollout).
- Perka support, "How can my customers use the Perka Beacon for hands-free
  check ins?"; Wikipedia, "Perka" (2018 rebrand to Clover Rewards).
- NearSight `research/sweep-2026-07-17-candidates.md`,
  `research/sweep-2026-08-23-candidates.md` (watchlist) and
  `research/sweep-2026-08-30-candidates.md` (promotion).
