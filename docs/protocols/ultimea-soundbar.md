# Ultimea soundbar system (CID 0x0D8C)

## Overview

**Ultimea Technology (Shenzhen) Limited** holds Bluetooth SIG company
identifier `0x0D8C`. Ultimea sells budget home-theatre soundbar systems and
projectors through Best Buy, Newegg, Staples and Amazon under retail model
numbers of the form `U2xxx`. Its soundbars carry Bluetooth 5.x for audio
streaming and an app-control channel, and the app-control radio advertises
the frame below continuously, with the product's **retail model number and
a per-unit serial in the clear**.

Four units on two models have been captured so far, on five separate days
between 2026-07-29 and 2026-08-29:

| First seen | Model code | Product (Best Buy listing) | Records · sightings |
|------------|-----------|-----------------------------|---------------------|
| 2026-07-29 | `U2601` | Aura A40 7.1ch virtual-surround soundbar system | 2 · 5 |
| 2026-07-31 | `U2502` | Poseidon M3T 5.1 soundbar system | 1 · 1 |
| 2026-08-20 | `U2601` | Aura A40 (second unit; seen again 08-22/23) | 4 · 8 |
| 2026-08-29 | `U2601` | Aura A40 (third unit) | 2 · 2 |

The 2026-08-23 NearSight sweep deferred the family at n=1 with the trigger
"ship when a 2nd unit appears"; the 08-29 capture met it, and a cumulative
re-merge of the telemetry corpus turned up the two older units.

## Supported models

| Model code | Product | Source |
|------------|---------|--------|
| `U2601` | Ultimea Aura A40 7.1ch soundbar system (bar + 4 surrounds + sub, 330 W) | Best Buy / Newegg listing "U2601" |
| `U2502` | Ultimea Poseidon M3T 5.1 soundbar system (bar + 2 rears + sub, 350 W) | Best Buy / Staples listing "U2502" |

Any other `U` + four-digit code parses with the code surfaced and **no**
product name claimed; extend the table only from a retail listing or a
named capture.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0D8C` (LE wire `8c 0d`) | SIG-assigned to *Ultimea Technology (Shenzhen) Limited* |
| Serial string | 11 ASCII bytes at [8..19) | `<model code 5><region 2><unit 4>`, e.g. `U2601USXXXX` |
| Address-shaped field | 6 bytes at [2..8) | Constant per unit; per-model prefix `d3:b1:ee` (U2601) / `f8:1b:20` (U2502). Not an IEEE OUI — reported raw |
| Service UUIDs | `0x260A` | Vanity 16-bit UUID co-advertised on every record; corroboration only |
| Address type | random, rotates between days | Same unit seen under two CoreBluetooth identifiers on 08-20 and 08-22 |
| Local name | none seen (corpus is nameless) | The soundbar's pairing name (`Aura A40`) is the Classic radio's, not this frame's |
| Device class | `soundbar` | |

## Ad Format — 20 bytes

```
offset  0  1 | 2  3  4  5  6  7  | 8  9  10 11 12 13 14 15 16 17 18 | 19
        8c 0d | d3 b1 ee xx xx xx | 55 32 36 30 31 55 53 xx xx xx xx | 01
        CID     address-shaped id   "U2601USXXXX"                      trailer
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0x0D8C` LE | 9/9 records |
| 2–7 | 6-byte per-unit id, address-shaped | Constant per unit across days; `d3:b1:ee:*` on all three U2601 units, `f8:1b:20:*` on the U2502. `d3` has the locally-administered bit set and neither prefix is IEEE-registered, so it is **not** called a factory MAC. Most plausibly the Classic BD_ADDR of the A2DP radio — not claimed |
| 8–12 | model code, `U` + 4 digits | `U2601` ×3 units, `U2502` ×1 |
| 13–14 | region code, 2 uppercase letters | `US` on all four (US-market units) |
| 15–18 | per-unit suffix, 4 alphanumerics | four distinct values across the four units — hex-looking; semantics not claimed |
| 19 | trailer | `0x01` on 9/9 records; reported raw, not gated |

### Parser gate

- company ID `0x0D8C`, **and**
- total length exactly 20, **and**
- bytes [8..19) all ASCII alphanumerics.

Any other `0x0D8C` shape is left unclaimed. If the 11 characters also match
the `U\d{4}[A-Z]{2}[0-9A-Z]{4}` grammar they are split into
`model_code` / `region_code` / `unit_suffix`; otherwise only `serial` is
reported.

## Identity Hashing

```
identifier = SHA256("ultimea_soundbar:{serial}")[:16]
stableKey  = "ultimea_soundbar:{serial}"
```

`serial`, `unit_suffix` and `device_address_hex` are tagged `uniqueStable`;
`model_code` is `modelIdentifying`. The unit that appeared on both 08-20 and
08-22 rotated its random address between the two days while the serial
string stayed put, which is exactly the case the payload-keyed identity is
for.

## What We Cannot Parse

- Power / input / volume state — nothing in the frame varies per sighting
- The meaning of the trailer byte and of the 4-character unit suffix
- Whether the address-shaped field is the Classic BD_ADDR
- Firmware version

## Detection Significance

A sighting means **an Ultimea home-theatre soundbar is powered on within
BLE range** — a living room. Because the serial is broadcast in the clear
from a rotating random address, the unit is trivially re-identifiable across
sessions, which the address rotation was presumably meant to prevent.

## Confidence / Attribution

**Vendor: high.** SIG company ID plus a payload model code that matches the
vendor's own retail model numbers on two different products.

**Product: high for `U2601` and `U2502`** (retail listings), none for any
other code.

**Field semantics: low** for the address-shaped field, the unit suffix and
the trailer — all reported raw.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x0D8C = Ultimea Technology
  (Shenzhen) Limited`.
- Best Buy: "Ultimea Aura A40 7.1ch Virtual Surround Sound Bar … Black
  U2601"; "Ultimea Poseidon M3T 5.1 Surround Sound Bar … Black U2502".
- NearSight `research/sweep-2026-08-23-candidates.md` (first unit,
  deferred) and `research/sweep-2026-08-30-candidates.md` (promotion, four
  units).
