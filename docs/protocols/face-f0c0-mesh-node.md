# 0xFACE / 0xF0C0 Mesh Node (vendor unidentified)

## Overview

A family of BLE nodes that advertise under the placeholder company ID
`0xFACE` and carry a 12-byte **node block** in service data under the
16-bit UUID `0xF0C0`. The block names how many nodes the sender knows, the
sender's own 6-byte node id and a 4-byte network tail; the manufacturer
frame is a typed gossip table listing up to two other nodes with a hop
count and each node's slowly-incrementing counter. Fourteen nodes were
captured in one three-minute scene on 2026-08-26 (23:55–23:58 UTC, RSSI up
to −56 dBm), every one on a rotating random address with no local name.

The 2026-06 `unidentified-beacons.md` entry "Nrdic<XXXXXX> / 0xFACE" was one
node of the same family (its block reads `06 01 | xxxxxxxxxxxx | 8f016800`
— six nodes, version 01, an id, a tail); that device also listed the
128-bit service UUID `F000F0C0-0451-4000-B000-000000000000`, which is the
Texas Instruments CC26xx SimpleLink base UUID with `0xF0C0` in the short
slot. Seventeen of this sweep's records list the same UUID. That points at
the silicon family (TI CC26xx), not at a vendor.

**No vendor is claimed.** `0xFACE` is not a SIG allocation, nothing in the
frames names a product, and the one local name ever seen ("Nrdic<XXXXXX>")
was a firmware-style default. The parser reports the protocol honestly and
keys identity on the node id.

Captured and shipped in the 2026-08-28 telemetry sweep
(NearSight `research/sweep-2026-08-28-candidates.md`).

## Supported Models

| Model | Attribution | Notes |
|-------|-------------|-------|
| unknown | none | 14 nodes in one 2026-08-26 scene + the 2026-06 "Nrdic<XXXXXX>" unit; identical block and frame grammar across all 15 |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0xF0C0`, exactly 12 bytes | byte 1 == `0x01`; bytes 2–7 non-zero |
| Company ID | `0xFACE` (wire `ce fa`) | placeholder, never sufficient alone |
| Service UUID (128-bit list) | `F000F0C0-0451-4000-B000-000000000000` | on 17 of 174 blocks; TI SimpleLink base — corroboration, not gated |
| Local name | none (2026-08); `Nrdic<XXXXXX>` (2026-06) | |
| Address | random, rotating | 14 CoreBluetooth identifiers for 14 node ids over three minutes |

### Node block (service data 0xF0C0, 12 bytes)

| Offset | Field | Size | Observed | Notes |
|--------|-------|------|----------|-------|
| 0 | node_count | 1 | `0d` (129 blocks), `0c` (11), `06` (2026-06) | how many nodes the sender currently knows — all 14 nodes agree on 13, dipping to 12 for a few seconds |
| 1 | version | 1 | `01` | gated on |
| 2–7 | node id | 6 | 14 distinct values | unique per unit; NOT a MAC — no registered OUI in either byte order, and the multicast/local bits are set on most |
| 8–11 | tail | 4 | `de 01 68 00` (all 14 nodes), `8f 01 68 00` (2026-06) | byte 8 differs between the two installs, `01 68 00` did not; reported raw |

### Manufacturer frame (CID 0xFACE)

Payload after the company ID is `[type] [seq] [own counter] …`:

| Type | Length | Body after `type seq counter` | Count |
|------|--------|-------------------------------|-------|
| `02` | 21 | `id ×6, hops, counter` × 2 | 8 |
| `03` | 24 | `01, id ×6, zeros` | 6 |
| `04` | 21 | `id ×6, hops, counter` × 2 | 45 |
| `06` | 25 | `51, tail ×4, fd ff 06 01, w16, w16, zeros` | 50 |
| `07` | 21 | `id ×6, hops, counter` × 2 (second slot often zero-filled) | 54 |

- `seq` walks `0x00`–`0x0f` and wraps.
- `own counter` is the sender's counter; it increments by 2 every 15–30 s.
- In every neighbour entry, `counter` equals that neighbour's *own*
  counter at that moment (checked across all 14 nodes) — the frame is a
  gossip table of "last heard from X at count N".
- `hops` takes 1, 2 or 3 (95 / 17 / 3 entries); the two nodes captured
  least often appear only at hops 2–3, consistent with hop distance from
  the sender.
- A zero-filled second slot means the sender had nothing to report; the
  same id can appear twice with two consecutive counters (a short history).
- Type `06`: the 4-byte tail from the node block recurs after a `51` byte,
  then `fd ff 06 01` and two small little-endian words (`0x0098`, `0x001b`
  on all 14 nodes; `0x0067`, `0x0019` on the 2026-06 unit). Meaning unknown;
  reported raw as `frame_body_hex`.

### Examples (node ids synthetic, everything else verbatim)

```
F0C0:  0d 01 | a1 a2 a3 a4 a5 a6 | de 01 68 00
mfg:   ce fa | 04 | 06 | 3a | b1 b2 b3 b4 b5 b6 01 2c | c1 c2 c3 c4 c5 c6 01 8e
              type  seq  own   neighbour 1   hops ctr   neighbour 2   hops ctr
mfg:   ce fa | 07 | 00 | b6 | b1 b2 b3 b4 b5 b6 01 34 | 00 00 00 00 00 00 00 00
mfg:   ce fa | 03 | 08 | c6 | 01 | b1 b2 b3 b4 b5 b6 | 00 × 12
mfg:   ce fa | 06 | 00 | b6 | 51 de 01 68 00 fd ff 06 01 98 00 1b 00 | 00 × 7
```

## Parser Scope (passive-only)

NearSight's `nrdic_face_beacon` (v2.0 — the name is kept from the 2026-06
single-device parser so persisted records keep their parser id) claims an
advertisement when the `0xF0C0` service data is exactly 12 bytes, byte 1
is `0x01` and the node id is non-zero. Manufacturer data is optional; when
present it must carry CID `0xFACE` (a foreign CID next to an F0C0 block is
declined). It is routed on both the CID and the `f0c0` service-data key so a
scan that delivers the block alone still lands. It reports:

| Field | Source |
|-------|--------|
| `vendor` | `unidentified` |
| `node_count`, `node_id`, `f0c0_tail_hex`, `service_data_f0c0_hex` | the node block; `node_id` tagged **unique, stable** |
| `frame_type_hex`, `frame_seq`, `own_counter_hex` | manufacturer payload bytes 0–2 |
| `neighbor_N_id`, `neighbor_N_hops`, `neighbor_N_counter_hex`, `neighbors` | types 02/04/07, zero slots skipped |
| `referenced_node_id`, `frame_flag_hex` | type 03 |
| `frame_body_hex` | any other type (06), raw |
| `device_name` | local name when present |
| `attribution_note` | the reasoning above |

Identity: `stableKey = nrdic_face_beacon:<node_id>`; device class
`mesh_node`; beacon type `face_f0c0_mesh_node`.

Not claimed: manufacturer frames delivered without the node block (23 of
163 in the capture — the same nodes, just a scan that missed the scan
response). `0xFACE` alone is the hobbyist placeholder and over-claims.

## Privacy

Each node advertises from a rotating random address and then broadcasts a
fixed 6-byte id — and its neighbours' ids — in the clear. The whole
installation is re-identifiable across sessions from any single node, and
the neighbour table leaks the network's topology to a passive listener.

## What We Cannot Parse

- Who makes it, or what it is. Fourteen co-located nodes with a
  membership count and hop-distance gossip reads as a commercial
  installation (lighting, sensing, access-control peripherals are all
  plausible); nothing in the bytes decides it.
- The type-06 words and the `51` byte; the meaning of the tail's first
  byte (per-network id is the natural reading — one value per install).
- Whether `hops` is hop distance or a link-quality bucket; the counter's
  unit.

## References

- NearSight `research/sweep-2026-08-28-candidates.md` — the 14-node capture
  and the frame analysis
- `docs/protocols/unidentified-beacons.md` — the 2026-06 "Nrdic<XXXXXX>" entry
  (one node of this family)
- NearSight `research/sweep-2026-07-01-candidates.md` — first note of the
  TI SimpleLink base UUID on that device
- Texas Instruments SimpleLink base UUID `F000xxxx-0451-4000-B000-000000000000`
  (CC26xx SDK)
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0xFACE` not assigned
