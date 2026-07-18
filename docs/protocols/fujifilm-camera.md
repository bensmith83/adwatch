# Fujifilm Camera — BLE Remote-Pairing Beacon

## Overview

Fujifilm cameras with Bluetooth LE connectivity to the FUJIFILM Camera
Remote companion app broadcast an advertisement keyed on Fujifilm's
Bluetooth SIG-registered company ID plus a model token embedded in the
local name. Verified against the SIG registry (a fresh `curl`, not the
cached copy) as **FUJIFILM Corporation** — note this is a different
registry from USB-IF, where `0x04D8` happens to belong to Microchip
Technology; the two should never be conflated.

## Fingerprint

### Company ID

| CID (LE-decoded) | SIG assignment |
|-------------------|-----------------|
| `0x04D8` | FUJIFILM Corporation |

### Local Name

Contains a known Fujifilm model token. Currently recognized: `X100VI` (a
real, current — 2024 — compact camera). Observed real capture:
`903BX100VI-903B` (the `903B` prefix/suffix is likely an internal
SKU/variant code; unconfirmed).

### Manufacturer Data

6 bytes after the CID (sweep 2026-07-17, n=1 distinct value):
`02 5a 07 00 00 00` — plausibly a minimal status/beacon frame; semantics
unconfirmed, surfaced as opaque metadata.

### Service UUID (when present)

A proprietary 128-bit vendor GATT service UUID was observed alongside:
`731893F9-744E-4899-B7E3-174106FF2B82` — not independently verifiable
against a public registry (128-bit UUIDs aren't SIG-allocated), not used
as a match anchor.

## Identification

- **Primary**: CID `0x04D8` **and** local name containing a known model
  token. CID alone is not enough (SIG-registered company IDs can appear
  on other Fujifilm product lines with unrelated advertisement shapes).
- **Device class**: `camera`.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `FUJIFILM Corporation` |
| Model | local-name token match | currently only `X100VI` |
| `payload_hex` | manufacturer data after CID | opaque, semantics unconfirmed |

## What We Cannot Parse

- Payload byte-level structure (n=1 sample, no field boundaries).
- Camera state (recording, connected, battery, shooting mode).
- What the `903B` local-name segments denote.

## Stable Identity

No confirmed per-unit identifier separate from the MAC. Anchored on
`stable_key = fujifilm_camera:<mac>`.

## References

- Bluetooth SIG `company_identifiers.yaml` — confirms `0x04D8 = FUJIFILM
  Corporation`: <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Fujifilm X100VI product page — confirms BLE connectivity to the
  FUJIFILM Camera Remote app.
