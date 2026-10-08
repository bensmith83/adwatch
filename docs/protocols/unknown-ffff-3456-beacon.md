# Unknown 0xFFFF / svc 0x3456 ASCII-ID Identity Beacon

## Overview

An unattributed family of BLE beacons whose entire manufacturer payload
(after the `ff ff` sentinel company id) is exactly **16 ASCII hex
characters** — an 8-byte unit id rendered as text — always
co-advertising the unassigned 16-bit service UUID **0x3456**. Nameless,
random address type on every capture.

First analysed on the 2026-10-07 NearSight nightly sweep. Full-history
evidence (re-merged corpus, 155k records): **11 records / 301 sightings /
4 distinct unit ids / 4 capture days, 2026-07-29 → 2026-10-06** — one
unit alone accounting for 222 sightings in a single day.

**No vendor is claimed.** CID `0xFFFF` is the SIG-reserved "no company
id" sentinel, squatted by many unrelated products (Meross, Viper,
Haier, Nothing, TimoTwo all ship 0xFFFF frames behind their own
secondary gates). Service UUID `0x3456` is unassigned. No local name
has ever been captured on the family, and the 8-byte id is not an
OUI-checkable MAC in either byte order (checked against the IEEE
registry). The shape — sentinel CID, vanity service UUID, ASCII-rendered
id — suggests a **DIY / dev-board identity beacon** (ESP32-class hobby
firmware or a provisioning helper), but that is a guess, not evidence,
so the family is catalogued as `vendor: Unknown` with the reasoning in
`attribution_note`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xFFFF` (wire `ff ff`) | SIG-reserved sentinel, not an attribution |
| Service UUID | `0x3456` | unassigned; present on all 11 records |
| Manufacturer payload | exactly 16 bytes, all `[0-9a-f]` ASCII | the unit id as text |
| Local name / service data | none | |
| Address | random | rotates; the ASCII id does not |

### Byte map (payload offsets, after the 2-byte CID)

| Offset | Field | Size | Observed |
|--------|-------|------|----------|
| 0–15 | unit id | 16 | ASCII hex chars; `78fdf4cacdc37045`, `997afe8dd79d03eb`, `8fb38d68656ff657`, `dc4166e58a0b0f35` |

### The unit id is rotation-stable identity

Unit `997afe8dd79d03eb` was captured from **two different BLE addresses
inside one 2026-07-29 capture window** (two upload-side device
identifiers, 3 + 26 sightings minutes apart). The ASCII id — not the
radio address — is the durable per-unit key, and the parser keys
identity on it (`stableKey = "unknown_ffff_3456:<id>"`,
payload-derived, in `payloadStableParsers`).

## Parser Scope

Passive advertisement parsing only. The parser
(`unknown_ffff_3456`, deviceClass `unknown`) is registered under the
`0x3456` service UUID — deliberately **not** the 0xFFFF CID, which is
already a multi-parser collision key — and re-checks in-parser: CID
0xFFFF AND svc 0x3456 AND a 16-byte all-ASCII-hex payload.

## Confidence

- **Family existence / structure: high** — 4 unit ids, 301 sightings,
  4 capture days across three months, byte-identical layout.
- **Vendor / product: none claimed** — no registry entry, name, or
  OUI evidence exists. A labelled specimen (a local name, a second
  correlated advertisement) would resolve it; the parser's
  `attribution_note` carries the reasoning until then.

## References

- NearSight `research/sweep-2026-10-07-candidates.md` — capture evidence
- `docs/protocols/unknown-0902-sensor.md` — the honest-unknown pattern
  this doc follows
