# CID 0x01B7 unattributed device population

## Overview

A population of BLE devices broadcasting 26-byte manufacturer data under
company ID `0x01B7`, which the Bluetooth SIG registers to **General
Electric Company** — but that registered-slot fact is the *only*
corroborating signal available. No local name, no service UUID/data, no
documented GE product layout matches this frame shape, and the cluster was
observed at a single site on a single day (2026-07-29). Per this project's
attribution-skepticism convention (see `cid-41a4-tracker.md`), the SIG
registration is recorded as metadata without being promoted to a vendor
claim.

What earns this a parser despite the unconfirmed vendor: it is not a
MAC-rotation artifact. The corpus shows **49 genuinely distinct, concurrent
`deviceIdentifier`s** with heavily overlapping observation windows and
*stable per-device payloads* — a real population of devices at one
location (a store, a fleet, an installed base of some product), not BLE
advertising noise.

## BLE Advertisement Format

### Identification anchors

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01B7` | Registered to General Electric Company — NOT treated as a vendor claim, see above |
| Protocol/version | `98 01` at bytes `[2..4)` | Constant, 49/49 |
| Marker | `5c 18` at bytes `[17..19)` | Constant, 49/49 |
| Tag-byte mask | `byte[22] & 0xE0 == 0xC0` | Holds for all 49 records; top 3 bits are a fixed tag, bottom 5 bits vary |

### Byte map (26 bytes)

```
b7 01 | 98 01 | <8-byte network_id> | <5-byte node_group> | 5c 18 | XX | <2-byte id_fragment> | XX | <3-byte rolling_id>
CID     [2..4)  [4..12) — see below   [12..17) low-card.    [17..19) [19]  [20..22)              [22] masked-gate  [23..26)
```

`[4..12)` (`network_id`) is emitted as metadata, **not** hard-gated —
unlike `CID41A4TrackerParser`'s family constants, we cannot yet tell
whether this 8-byte block is a stable product-family constant (safe to
lock on) or a deployment/site-specific key (would site-lock the parser to
this one location if hard-coded). Revisit once a second site's data
exists — see the follow-up bead filed alongside this sweep
(`adwatch-app-hh3r` in the app repo).

### What we can extract

| Field | Notes |
|-------|-------|
| `protocol_version` | `[2..4)`, constant |
| `network_id_hex` | `[4..12)`, metadata only, not gated |
| `node_group_hex` | `[12..17)`, low-cardinality (3-4 distinct values per byte across the 49 devices) |
| `tag_hex` | `[19]`, 14 distinct values observed |
| `id_fragment_hex` | `[20..22)`, high entropy |
| `tag_byte_hex` | `[22]`, high entropy in the low 5 bits, but always masks to `0xC0` in the top 3 |
| `rolling_id_hex` | `[23..26)`, high entropy |

### What we cannot extract

- Vendor / product confirmation (the GE registry match is the only signal;
  explicitly not claimed — `vendor: "Unknown (unconfirmed despite
  registered CID)"`)
- Any semantic meaning for `node_group`, `tag`, `id_fragment`, or
  `rolling_id` beyond their raw values

## Detection significance

- Real signal of a device population, not noise: 49 concurrent, distinct
  devices at one site with stable-not-random payloads is exactly the shape
  a genuine deployed product fleet would produce (asset tags, retail
  fixtures, or similar).
- Two co-occurring unattributed clusters in the same capture burst
  (`0xb10a`, `0xb1cd`, `0xcac2` — see `research/sweep-2026-07-30-candidates.md`
  in the app repo) suggest the same venue and possibly the same underlying
  product family; not yet investigated together.

## References

- Bluetooth SIG company-identifier registry (General Electric Company,
  `0x01B7`).
- Captures: `research/telemetry-merged.json`, 2026-07-30 sweep
  (`research/sweep-2026-07-30-candidates.md` in the app repo).
- House precedent for shipping a registered-but-unconfirmed CID as a
  fingerprint rather than a vendor claim: `cid-41a4-tracker.md`.
