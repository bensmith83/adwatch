# Unknown 0xB1BB service-data-only rotating presence beacon

## Overview

A swarm of **56 distinct devices** observed together in one environment on a
single day (2026-06-13, 524 sightings) in the 2026-06-15 NearSight sweep, each
advertising **service data under the 16-bit UUID `0xB1BB`** and nothing else —
no manufacturer data, no local name, random address.

This is the **service-data-only sibling** of the already-cataloged
`unknown-bcb1` / `unknown-cdb1` family. Those documents cover the
*manufacturer-data* members (vanity company IDs `0xb1bc` / `0xb1cd`) which are
"frequently paired with a service-data entry under 16-bit UUID B1BB". The 56
devices here advertise **only** the B1BB service data.

## Vendor attribution

**Unattributed.** `0xB1BB` is **not** SIG-allocated (the SIG member-UUID range
is `0xFC31`–`0xFEFF`; `0xB1BB` is far below it and absent from
`member_uuids.yaml`). No public source attributes 0xB1BB to any named app or
device. Every privacy-preserving presence network was positively ruled out by
UUID: Exposure Notification (`0xFD6F`), Google Find My Device / FMDN
(`0xFEAA`), Tile (`0xFEED`), Samsung SmartTag (`0xFD5A`). We do not fabricate a
vendor.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID | `0xB1BB` (not SIG-allocated) |
| Service-data length | exactly **27 bytes** |
| Service-data prefix | leading bytes `b1 bb` (then 25-byte body) |
| Manufacturer data | **absent** (distinguishes from the 0xb1bc/0xb1cd siblings) |
| Local name | absent |
| Address type | random |

Sample (one device): `b1bb4746de1e233dd94fcb792abe3d534df58e0922cab2020d7f26`.

### Structure

```
b1 bb | 47 46 de 1e 23 3d d9 4f cb 79 … (25 bytes)
\_____/ \____________ rotating token ____________/
 prefix         opaque / high-entropy
```

The 25-byte body is fully rotating across devices (51/56 distinct first body
bytes) — characteristic of an **encrypted/ephemeral rotating identifier**.
That signature — many co-located random-address devices each emitting an
opaque rotating token as 16-bit Service Data with no name and no mfg data — is
structurally a **privacy-preserving presence / proximity beacon** of unknown
vendor.

## Parser scope

Passive decode only. Gate: B1BB service data present, exactly 27 bytes, `b1bb`
prefix, **and** the device is not also carrying the `0xb1bc`/`0xb1cd` vanity
CID (those defer to `UnknownBCB1Parser` / `UnknownCDB1Parser` — no
double-claim). Surface `service_b1bb_hex`, the 25-byte `rotating_token_hex`,
`sig_status`, and an honest `category = rotating_presence_beacon`. No vendor
set. Stable key is `unknown_b1bb:<MAC>` — the token rotates and the address is
random, so no per-device anchor exists.

## Confidence

- Structural classification (rotating presence beacon): **medium-high** (by
  analogy; UUID matches none of the known presence networks).
- Vendor: **none**.

## Next steps

Active investigation would be required to positively ID: check whether the
random address is a resolvable RPA vs non-resolvable, whether the token
rotates in lockstep with the address (→ encrypted ephemeral ID), and a
GATT-connect to enumerate services.

## References

- Sibling docs: `docs/protocols/unknown-bcb1.md`, `docs/protocols/unknown-cdb1.md`.
- NearSight app: `Sources/Parsers/UnknownB1BBParser.swift`,
  `research/sweep-2026-06-15-candidates.md`.
- BT SIG `member_uuids.yaml` (0xB1BB absent → not SIG-allocated).
