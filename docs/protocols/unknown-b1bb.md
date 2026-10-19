# Unknown 0xB1BB service data: stationary store-infrastructure mesh node

## Overview

Devices advertising **service data under the 16-bit UUID `0xB1BB`**, with no
manufacturer data, no local name and a random address. First seen in June 2026
as a 56-device swarm in one environment and originally written up as a
"rotating presence beacon". A much larger capture in October 2026, inside a US
department store over about two hours, shows that reading was wrong.

These are **stationary infrastructure nodes of a managed-flood BLE mesh**, most
plausibly a shelf-label (ESL) network or a lighting-control network. They are
not personal devices and not a privacy-preserving presence beacon. The vendor
is **unattributed**.

The same mesh also emits the manufacturer-data frames documented in
[`unknown-bcb1.md`](unknown-bcb1.md) (vanity CID `0xb1bc`) and
[`unknown-cdb1.md`](unknown-cdb1.md) (vanity CID `0xb1cd`). Those are flood
relays and one-shot flood messages from the same nodes (see below).

## Identification

| Signal | Value |
|---|---|
| Service UUID | `0xB1BB` (not SIG-allocated) |
| Service-data length | exactly **27 bytes** |
| Service-data prefix | `b1 bb` (magic, mirrors the UUID) |
| Manufacturer data | absent on the service-data-only members; the `0xb1bc` / `0xb1cd` members carry it and are handled by their own parsers |
| Local name | absent |
| Address type | random |

`0xB1BB` is far below the SIG member-UUID range (`0xFC31`-`0xFEFF`) and absent
from `member_uuids.yaml`. Exposure Notification (`0xFD6F`), Google FMDN
(`0xFEAA`), Tile (`0xFEED`) and Samsung SmartTag (`0xFD5A`) were ruled out by
UUID.

## Byte map (27-byte service data)

| Offset | Size | Role | Behaviour |
|---|---|---|---|
| 0..2 | 2 | magic `b1 bb` | constant |
| 2 | 1 | group / site id (part 1) | persistent, shared by every node of a group |
| 3..14 | 11 | per-node id | unique to a node, stable for at least 100 minutes |
| 14 | 1 | per-group, per-epoch | changes for the whole group at once |
| 15..18 | 3 | per-node id (part 2) | unique to a node, stable |
| 18..23 | 5 | group / site id (part 2) | persistent, shared by the group |
| 23..26 | 3 | rolling counter / nonce | changes about once a second |
| 26 | 1 | per-group, per-epoch | changes for the whole group at once |

Masked example (`g` = group/site id, `n` = per-node id, `e` = per-epoch,
`r` = rolling):

```
b1bb  gg  nnnnnnnnnnnnnnnnnnnnnn  ee  nnnnnn  gggggggggg  rrrrrr  ee
magic [2] [3..14) 11 bytes        [14] [15..18) [18..23)  [23..26) [26]
```

Evidence: in snapshot-to-snapshot diffs of the nodes, about half changed only
bytes 23-25. Roughly a quarter of the nodes were in view continuously for 20
minutes or more. The only part that looks random from second to second is the
3-byte rolling field. Treating the whole body as a rotating token (the old
reading) came from a short capture in which each node was seen only once or
twice.

## Relationship to the `0xb1bc` flood relays

The `0xb1bc` manufacturer-data frames (19-byte body) decompose as a **9-byte
message id + 3-byte relay-variable field (hop/TTL-like, unconfirmed) + 7-byte
tail**. Many nodes relay the same message id inside one second (23 distinct
nodes sent one id in the same second in the capture), and the next message
appears about a second later. That is the signature of managed flooding, not
of one device emitting a unique token. Because the message id is shared across
relaying nodes, it is not a per-device identity; the service-data node id
(bytes 3..14 plus 15..18) is.

## Note on `0xb1cd`

The `0xb1cd` manufacturer-data "bodies" are one-shot flood messages too: in one
September 2026 burst, 72 records that shared one exact body carried distinct
B1BB node ids, so one body is a message seen from many nodes, not one device.
An earlier write-up said the co-emitted B1BB values were **30 bytes**; that is
wrong. They are **27 bytes**, the same shape as here.

## Scale observed

In a single department-store visit (about two hours): roughly 520 distinct BLE
identities, about 520 distinct node ids, **about 226 distinct group ids**, and
about 22,000 sightings. Elsewhere the family appears only as short bursts
during store hours in other buildings. Group ids seen in a September visit to
the same store recurred in the October visit (about three quarters of that
day's groups), so group ids persist across weeks.

## Parser scope

Passive decode only. NearSight's `unknown_b1bb` parser gates on B1BB service
data of exactly 27 bytes with the `b1 bb` prefix, and defers if the device also
carries the `0xb1bc` / `0xb1cd` CID (those go to the bcb1 / cdb1 parsers, so
nothing is double-claimed). It surfaces the raw hex fields,
`sig_status = not_sig_allocated` and `category = store_infrastructure_mesh`.
Vendor is left unset. The device class is `mesh_node` (shown as "Store Mesh
Node"), so a store full of nodes collapses into one counted entry instead of
hundreds of "unknown" devices. The stable key is the address, which does not
rotate for these stationary nodes.

## Privacy note

**The group id (byte 2 and bytes 18..23) is a persistent site fingerprint.** It
is shared by every node of a group and recurs across visits weeks apart.
Implementations should **not** build "you were here before" or location-recall
features on it, and should not log or upload it beyond what a raw-hex debug
field requires. The per-node id identifies fixed infrastructure, not a person.

## Confidence and attribution

- Stationary managed-flood infrastructure mesh: **high** (long dwell times,
  persistent group ids across visits, byte-level stability pattern, many nodes
  relaying one message id within a second).
- Byte roles (map above): **medium-high**, inferred from variation across
  snapshots, not from a spec. The "epoch" and "hop/TTL" labels are guesses.
- Application, ESL network versus lighting control (a Casambi-like system is
  one candidate): **unresolved**. No standard ESL service (`0x1857`) or known
  ESL vendor frame was seen from these nodes.
- Vendor: **none**. No public source ties `0xB1BB`, `0xb1bc` or `0xb1cd` to a
  product. Resolving it would need active work (GATT connect, a labelled
  fixture), which this passive project does not do.

## References

- Sibling docs: [`unknown-bcb1.md`](unknown-bcb1.md), [`unknown-cdb1.md`](unknown-cdb1.md).
- NearSight app: `Sources/Parsers/UnknownB1BBParser.swift`.
- BT SIG `member_uuids.yaml` (`0xB1BB` absent, so not SIG-allocated).
