# Unknown BLE Family — CID `0x0A01` + FEBE Service UUID

## Overview

A BLE family that co-advertises Bluetooth SIG company ID **`0x0A01`**
alongside the SIG-member service UUID **`0xFEBE`**. Both signals point at
a named vendor — but at *different* named vendors that have no documented
relationship, so the family is catalogued here as `vendor: Unknown` and a
fingerprint-only parser (`unknown_febe_0a01`) is provided.

- `0xFEBE` is **Bose Corporation's** SIG-registered service UUID (the same
  UUID that routes real Bose earbuds through `BoseFEBEEarbudsParser`), so
  on its own it would suggest Bose.
- `0x0A01` is SIG-assigned to **Cleveron AS** — an Estonian parcel-locker
  / delivery-robot company — a vendor with no known BLE-audio product line
  and no documented relationship to Bose.

This is the **third** instance of this exact CID+FEBE ambiguity shipped in
this codebase: `unknown_febe_0601` (Bose vs. Schrader Electronics) and
`unknown_febe_0b01` (Bose vs. Resideo Technologies) are the siblings.
Rather than guess which company actually built the device, we withhold
attribution and surface both candidates plus the reasoning via an
`attribution_note`.

This parser is deliberately named `unknown_febe_0a01`, **not**
`unknown_febe`: the bare FEBE service UUID alone already routes to real
Bose devices via `BoseFEBEEarbudsParser`, so this parser is scoped to the
**`0x0A01` + FEBE** combination specifically.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `0xFEBE` | SIG-member service UUID, registered to Bose Corporation. Required alongside the CID for this parser to claim. |

### Company ID

| CID (LE-decoded) | On-wire bytes | SIG assignment |
|------------------|---------------|----------------|
| `0x0A01` | `01 0a` | Cleveron AS |

### Manufacturer Data

6 records observed (sweep 2026-07-17), CID + 7-byte payload each:

```
01 0a 42 00 <5-byte tail>
└──┬─┘ └┬─┘ └────┬──────┘
  CID   hdr   opaque tail
```

- **Bytes 0–1**: `01 0a` on wire → LE-decoded CID `0x0A01`.
- **Bytes 2–3**: constant `42 00`, stable across all 6 records.
- **Bytes 4–8**: 5-byte tail, semantics unknown. Two pairs show a partial
  byte-overlap across records captured hours apart (e.g. one record's
  tail shares 4 bytes with another's, shifted by one byte position), but
  the underlying 40-bit values are not monotonic by timestamp — ruling
  out a simple counter. Surfaced as opaque payload, not asserted to be
  decoded further.

### Local Names

No local name captured on any of the 6 records.

## Identification

- **Primary**: CID `0x0A01` **and** service UUID `0xFEBE` co-advertised.
  The parser guards on both; neither alone triggers a claim.
- **Secondary** (informational): the constant `42 00` header confirms the
  frame is in its expected shape.
- **Device class**: `unknown` — fingerprint-only, no vendor or product
  claim.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Family flag | CID `0x0A01` + service UUID `0xFEBE` | "We've seen this family before" |
| Header (`42 00`) | mfr bytes 2–3 | constant across observed captures |
| Payload tail | mfr bytes 4–8 | 5 bytes of per-record data; semantics unknown |
| `attribution_note` | derived | records the Bose-vs-Cleveron tie and why attribution is withheld |

## What We Cannot Parse

- Vendor / brand / product class — attribution is deliberately withheld.
- Semantics of the 5-byte tail, including the partial-overlap pattern
  noted above.

## Stable Identity

No confirmed per-unit identifier in the advertisement. Anchored on the BLE
MAC — `stable_key = unknown_febe_0a01:<mac>`.

## References

- Bluetooth SIG company identifiers (YAML mirror) — confirms
  `0x0A01 = Cleveron AS`:
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Bluetooth SIG member UUIDs (YAML mirror) — confirms
  `0xFEBE = Bose Corporation`:
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml>
- Companion / sibling parsers in this codebase:
  - `UnknownFEBE0601Parser` — Bose vs. Schrader Electronics.
  - `UnknownFEBE0B01Parser` — Bose vs. Resideo Technologies.
  - `BoseFEBEEarbudsParser` — the FEBE-attributed Bose family this parser
    deliberately does **not** join.
