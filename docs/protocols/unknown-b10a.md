# Unknown `0xb10a` Vanity-CID Beacon (Fixed 19-Byte Frame, Per-Advertisement MAC Rotation)

## Overview

A BLE emitter observed in the 2026-07-31 NearSight telemetry sweep: **32 records, every one on a different CoreBluetooth identifier**, 63 sightings total, each broadcasting a 19-byte manufacturer-data frame whose little-endian company identifier decodes to `0xb10a`.

The SIG company-identifier registry tops out at `0x10F4` (3,987 entries, fetched 2026-07-31), so `0xb10a` is far above the assigned range — **definitively vanity-forged / unregistered**.

This is the fourth member of the `XX b1` vanity-CID family already catalogued in this repo:

| Parser | Key | Wire bytes | Frame |
|--------|-----|-----------|-------|
| [`unknown_cdb1`](unknown-cdb1.md) | CID `0xb1cd` | `cd b1` | fixed 26-byte |
| `unknown_bcb1` | CID `0xb1bc` | `bc b1` | 21-byte |
| [`unknown_b1bb`](unknown-b1bb.md) | service UUID `B1BB` | `b1 bb` | 27-byte service data |
| **`unknown_b10a`** (this doc) | CID `0xb10a` | `0a b1` | fixed-mask 19-byte |

All four share the same behavioural signature: an unregistered `XX b1`-shaped identifier, aggressive MAC rotation, and an opaque rotating body.

**Vendor: not attributed.** Registry lookup confirms `0xb10a` is unassigned, and no public documentation was found for the `0ab164` prefix or the `01 13 00 00 05 1a 00` frame constant. The family resemblance is recorded as a structural hint in metadata, explicitly **not** as a shared-vendor claim.

### Capture context

All 32 records fall in a single window on 2026-07-29, **19:45:53Z → 20:28:05Z** (~42 minutes). The 2026-07-30 sweep had already parked this cluster (with the same record count) alongside `cid:0xb1cd` and `cid:0xcac2` as uninvestigated, describing the three as co-occurring in one "~23-second capture burst". The measured windows are same-day but distinct — `0xb1cd` at 17:06–17:13, `0xb10a` at 19:45–20:28, `0xcac2` at 03:56–04:00 the following morning. Consistent with one venue over one day; **not** one burst, so a shared-product-family inference across the three CIDs has less support than that framing implied.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xb10a` | NOT SIG-assigned (max assigned `0x10F4`). LE wire bytes `0a b1`. |
| Manufacturer-data total length | 19 bytes | 2-byte CID + 17-byte payload; 32/32 |
| Payload byte [0] | `0x64` | 32/32 |
| Payload bytes [7..13] | `01 13 00 00 05 1a 00` | 32/32 |
| Local name | absent | 32/32 |
| Service UUIDs | absent | 32/32 |
| Address type | random | New address per advertisement |

### Wire Layout

```
0a b1 | 64 | 81 | R R R R | F | 01 13 00 00 05 1a 00 | 0c | V V
\__ _/  \_/  \_/  \__ ___/ \_/  \_______ ___________/ \_/  \_/
   \/    |    |      \/     |           \/             |    \/
 LE CID  |  variant  |    flags     7-byte constant    |  variable
 0xb10a  |           |                                 low-cardinality
      constant   rotating 4-byte value
       0x64      (~unique per record)
```

Ten of the nineteen bytes are byte-identical across every capture.

### Per-Byte Constancy (all 32 records)

| Offset | Distinct values | Observed |
|--------|-----------------|----------|
| 0–1 | 1 | `0a b1` (CID) |
| 2 | **1** | `0x64` |
| 3 | 2 | `0x81` (30), `0x01` (2) |
| 4 | 31 | rotating |
| 5 | 29 | rotating |
| 6 | 29 | rotating |
| 7 | 31 | rotating |
| 8 | 5 | `0x82` (16), `0xc0` (8), `0x81` (5), `0x80` (2), `0xc2` (1) |
| 9–15 | **1** each | `01 13 00 00 05 1a 00` |
| 16 | 4 | `0x0c` (13), `0x0d` (9), `0x0a` (5), `0x07` (5) |
| 17 | 22 | variable |
| 18 | 28 | variable |

Byte [8] taking only high-nibble `8` and `c` values is bitfield-shaped, hence `flags_byte` in metadata — but it is reported, not interpreted.

Bytes [16..18] read as a 24-bit big-endian value land in a narrow band (`0x0a8175` … `0x0d9372`) across the capture, which is consistent with a counter or a truncated timestamp. Thirty-two samples inside a single scan window does not establish monotonicity, so it is surfaced as `counter_hex` and left uninterpreted.

### Real Captures

```
0ab1 64 81 e510591c 82 01130000051a00 0a7df5
0ab1 64 81 ddc817e5 82 01130000051a00 0a8244
0ab1 64 81 ff995977 80 01130000051a00 0d030f
0ab1 64 81 96705fe7 80 01130000051a00 0d0815
0ab1 64 01 6b8ff399 82 01130000051a00 0c7ab8
0ab1 64 01 5a75a9b2 82 01130000051a00 0c6604
```

## Detection Strategy

Gate on **CID + payload length 17 + `payload[0] == 0x64` + the exact 7-byte constant at `payload[7..<14]`**.

The vanity CID alone is far too false-positive-prone — anyone can squat `0xb10a`, and this repo has a documented history of vanity-CID collisions. The two constant runs are the load-bearing anchor.

Unlike [`unknown_cdb1`](unknown-cdb1.md), this parser does **not** anchor on an exact body. That parser had exactly one bit-pattern sample and could not distinguish fixed from variable bytes, so it over-fit deliberately. Here we have 32 independent samples, which is enough to separate the constant mask from the rotating region — so the constant mask is what the gate uses. This is the "relax to a fixed-vs-variable mask" upgrade path `unknown_cdb1`'s header describes, applied from the start because the data supports it.

## Stable Identity

Every capture had a distinct MAC **and** a distinct rotating region, so neither yields a cross-advertisement identity. Identity therefore keys on the address, producing one identity per observed advertisement:

```
identifierHash = sha256_16("unknown_b10a:<mac>")
stableKey      = nil
```

This is the same choice [`CID41A8TrackerParser`](../../Sources/Parsers/CID41A8TrackerParser.swift) makes for its rotating-address tracker family. Note the consequence: anything matching this parser is by construction MAC-uncoordinated and should be excluded from MAC-based dwell/unique-device counts.

## Research Leads (July 2026)

| Search | Outcome |
|---|---|
| SIG `company_identifiers.yaml` for `0xb10a` / `0x0ab1` | Absent. Registry max is `0x10F4` (3,987 entries, 2026-07-31). |
| `0ab164`, `0ab16481` as a manufacturer-data prefix | No documented hits. |
| Frame constant `01 13 00 00 05 1a 00` | No documented hits. |
| AltBeacon spec cross-check | Rejected — AltBeacon requires `0xbeac` at body bytes [0..1]; ours are `64 81`. |
| Known crowd-locate ecosystems (Apple FindMy `FE9F`, Google FMDN `fcf1`, Samsung `FD5A`, Tile `FEED`) | None publishes a `0xb10a` signature. |
| Sibling family (`0xb1cd`, `0xb1bc`, `B1BB`) bodies | No byte overlap with this frame beyond the shared `XX b1` CID shape. |

## What We Cannot Parse

- **Vendor / model.** No public match. Best path forward: a labelled specimen, or a connected GATT session reading the device-information service.
- **The rotating 4-byte region.** Effectively unique per advertisement; could be a rotating pseudonym, a nonce, or a truncated hash. Thirty-two samples from a single scan window cannot distinguish these.
- **Whether the 32 identifiers are 32 devices.** Given per-advertisement MAC rotation, they are almost certainly far fewer physical emitters — but with a rotating body there is no cross-advertisement linkage to prove it, unlike `unknown_cdb1` where the identical body collapsed 37 records to one device.

## References

- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0xb10a` absent; max assigned `0x10F4` as of 2026-07-31.
- [`unknown-cdb1.md`](unknown-cdb1.md) — sibling `0xb1cd`, exact-body variant of the same family.
- [`unknown-b1bb.md`](unknown-b1bb.md) — sibling service-data surface.
- [`Sources/Parsers/CID41A8TrackerParser.swift`](../../Sources/Parsers/CID41A8TrackerParser.swift) — MAC-keyed identity exemplar for rotating-address emitters.
- `research/sweep-2026-07-31-candidates.md` (NearSight app repo) — cluster evidence and per-byte frequency tables.
