# Axon Enterprise encrypted broadcast (service UUID 0xFC81)

## Overview

**Axon Enterprise, Inc.** holds the Bluetooth SIG *member* 16-bit service
UUID `0xFC81` — a *second* Axon allocation alongside `0xFE6B` (registered
to "TASER International, Inc.", Axon's former name; see
[axon-fe6b.md](axon-fe6b.md)). Member UUIDs are allocated only to SIG
member companies, so the UUID itself is the vendor attribution.

73 records in the 2026-09-19 merged corpus carry 27-byte service data
under `0xFC81` — the largest single cluster in that corpus's unparsed
pool. Every record is a one-off sighting at −83..−97 dBm from a random
address with no local name: hardware on the move, consistent with Axon's
body-worn cameras, in-car/fleet systems, or another product in the same
family. Which product emits these frames is not recoverable passively.

## Supported models

None pinned. The frames name no model and no Axon document describes the
broadcast. Reported as the Axon family with the product left open — the
same posture as `axon-fe6b`.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFC81` | SIG member UUID → *Axon Enterprise, Inc.* — the whole attribution |
| Address type | random, one sighting per record | 73 records, 73 sightings, zero repeated payloads |
| Local name | none | |
| Device class | `surveillance` | Same class as `axon_fe6b` |

## Ad Format — 27 bytes, one observed shape

```
[0]      flags/type — 0x80..0x83 observed (high 6 bits constant)
[1]      entropy (67 distinct values across 73 records)
[2]      flags/type — 0xc9..0xcb observed (high 6 bits constant)
[3..5)   0x81 0x0c (CONSTANT on all 73 records — the structural gate)
[5..27)  high entropy — rotating/encrypted body
```

The entropy region contains **no recoverable unit identity**: zero
duplicate full payloads across the cluster and no repeated 6-byte window
between any two records. This looks like an ephemeral-ID / encrypted
broadcast (Axon's equivalent of the offline-finding frames other vendors
emit), not a serial-numbered advertisement.

### Parser gate

`0xFC81` service data of exactly 27 bytes with `[3..5) == 81 0c`. The
flags bytes are reported raw (`flags_0_hex`, `flags_2_hex`); the body is
reported raw as `ciphertext_hex` with `decode: header_only`.

## Identity Hashing

```
identifier = SHA256(ble_address + ":" + payload_hex)[:16]
stableKey  = nil
```

Nothing in the payload is stable, so identity deliberately mixes the BLE
address *with* the payload (the `apple_continuity` pattern): a rotated
frame from one address and the same frame echoed from another address are
both distinct sightings. The parser is consequently **not** on
`StableDeviceKey.payloadStableParsers` — there is no payload-derived
stable identity to anchor on.

## What We Cannot Parse

- Which Axon product emits these frames
- The meaning of the two flags bytes (type vs. counter bits)
- The body (encrypted/rotating by design)
- Any state or telemetry

## Detection Significance

A sighting means **Axon hardware is within BLE range** — a body-worn
camera, an in-car/fleet system, or a related device. Records are one-off
drive-bys; no unit can be re-identified across sightings.

## Confidence / Attribution

**Vendor: high.** A SIG member service UUID registered to Axon on every
record, with a structural constant (`81 0c`) verified across all 73.

**Product: low / not claimed.** Family-level claim only.

**Field semantics: low.** Flags and body are reported raw; only the
constant's position is asserted.

## References

- Bluetooth SIG `member_uuids.yaml` — `0xFC81 = Axon Enterprise, Inc.`
- NearSight `AxonFC81Parser` (`Sources/Parsers/AxonFC81Parser.swift`,
  shipped 2026-09-19) and `research/sweep-2026-09-19-candidates.md` —
  the sweep that identified and shipped this cluster.
- [axon-fe6b.md](axon-fe6b.md) — Axon's other member-UUID broadcast,
  with a decodable unit ID.
