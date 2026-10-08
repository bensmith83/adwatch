# Unknown BLE Family — CID `0x0B01` + FEBE Service UUID

## Overview

A BLE family that co-advertises Bluetooth SIG company ID **`0x0B01`**
alongside the SIG-member service UUID **`0xFEBE`**. Both signals point at a
named vendor — but at *different* named vendors that have no documented
relationship, so the family is catalogued here as `vendor: Unknown` and a
fingerprint-only parser (`unknown_febe_0b01`) is provided.

- `0xFEBE` is **Bose Corporation's** SIG-registered service UUID (the same
  UUID that routes real Bose earbuds through `BoseFEBEEarbudsParser`), so on
  its own it would suggest Bose.
- `0x0B01` is SIG-assigned to **Resideo Technologies, Inc.** — the Honeywell
  Home security/comfort spinoff — a vendor with no known BLE-audio product
  line and no documented relationship to Bose.

Neither vendor's fingerprint confidently explains the *other* vendor's
signal, and the captured local names don't break the tie (see below). Rather
than guess which company actually built the device, we withhold attribution
and surface both candidates plus the reasoning via an `attribution_note`, so
a labelled specimen can resolve it later — the same withheld-attribution
pattern as the sibling `unknown_febe_0601` family (Bose vs. Schrader
Electronics).

This parser is deliberately named `unknown_febe_0b01`, **not** `unknown_febe`:
the bare FEBE service UUID alone already routes to real Bose devices via
`BoseFEBEEarbudsParser`, so this parser is scoped to the **`0x0B01` + FEBE**
combination specifically and must not shadow that broader FEBE family.

## Fingerprint

### Service UUID

| UUID | Notes |
|------|-------|
| `0xFEBE` | SIG-member service UUID, registered to Bose Corporation. Required alongside the CID for this parser to claim. |

### Company ID

| CID (LE-decoded) | On-wire bytes | SIG assignment |
|------------------|---------------|----------------|
| `0x0B01` | `01 0b` | Resideo Technologies, Inc. (Honeywell Home spinoff) |

### Manufacturer Data (when present)

One 9-byte manufacturer-data frame observed (CID + payload):

```
01 0b 02 00 xx xx xx xx xx
└──┬─┘ └─┬─┘ └─────┬──────┘
  CID   hdr     5-byte tail
```

- **Bytes 0–1**: `01 0b` on wire → LE-decoded CID `0x0B01` (Resideo).
- **Bytes 2–3**: constant `02 00` header, stable across observed captures.
- **Bytes 4–8**: a 5-byte tail that is **stable within one capture session
  per unit** but whose semantics are unknown (counter? truncated MAC?
  per-unit token? sensor word?). We surface it as opaque payload rather than
  guess.

### Local Names

Captured local names include `"LE-reserved_C"`. This looks like a
device-generated / iOS-side placeholder rather than a real product name, so
it is **not** treated as a meaningful attribution or product signal — it does
not favour either candidate vendor and is surfaced only as raw
`local_name` metadata.

## Identification

- **Primary**: CID `0x0B01` **and** service UUID `0xFEBE` co-advertised. The
  parser guards on both; neither alone triggers a claim (FEBE alone belongs
  to the broader Bose family).
- **Secondary** (informational): the constant `02 00` header confirms the
  frame is in its expected shape.
- **Device class**: `unknown` — the parser is fingerprint-only and makes no
  vendor or product claim.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Family flag | CID `0x0B01` + service UUID `0xFEBE` | "We've seen this family before" |
| Header (`02 00`) | mfr bytes 2–3 | constant across observed captures |
| Payload tail | mfr bytes 4–8 | 5 bytes of per-unit data; semantics unknown |
| `attribution_note` | derived | records the Bose-vs-Resideo tie and why attribution is withheld |

## What We Cannot Parse

- Vendor / brand / product class — attribution is deliberately withheld; no
  labelled specimen yet.
- Semantics of the 5-byte tail (counter? truncated MAC? per-unit token?).
- Whether the device is audio hardware (implied by FEBE/Bose), a
  comfort/security device (implied by the Resideo CID), or something else
  entirely.

## Stable Identity

There is no confirmed per-unit identifier in the advertisement: the 5-byte
tail is stable only within a single capture session, so it can't be trusted
as a durable serial across sessions. We therefore anchor identity on the BLE
MAC for now — `stable_key = unknown_febe_0b01:<mac>` — so distinct physical
units don't collapse into one card. Re-grouping across MAC rotations will
need richer payload sampling in the future.

## References

- Bluetooth SIG company identifiers (YAML mirror) — confirms
  `0x0B01 = Resideo Technologies, Inc.`:
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Bluetooth SIG member UUIDs (YAML mirror) — confirms
  `0xFEBE = Bose Corporation`:
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml>
- Companion / sibling parsers in this codebase:
  - `UnknownFEBE0601Parser` — the sibling withheld-attribution FEBE family
    (Bose vs. Schrader Electronics) whose style this parser mirrors.
  - `BoseFEBEEarbudsParser` — the FEBE-attributed Bose family this parser
    deliberately does **not** join.
