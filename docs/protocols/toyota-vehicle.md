# Toyota / DENSO TEN In-Vehicle BLE Module

## Overview

A Toyota in-vehicle BLE module observed in the 2026-07-06 sweep advertising
manufacturer data under **CID `0x010D` = DENSO TEN Limited** (a Toyota-group
automotive-electronics supplier — head units, telematics, keyless/PEPS modules)
with a self-identifying localName `TOYOTA RAV4`. **Low-trust-sourced** (see the
sweep write-up).

## Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x010D` | SIG-assigned to **DENSO TEN Limited**; supplies multiple makes → vendor-level anchor |
| Local name | `TOYOTA <model>` (e.g. `TOYOTA RAV4`) | carries the model attribution |
| Address type | random | |
| Device class | `vehicle` | |

## Manufacturer data

Example: `0d01 c0acd2dc1eaf68ed72afdf4bf1d918313260b0` (CID `0x010D` + 19-byte
body). The body is treated as **opaque** — only two captures, and it may be a
rolling/encrypted PEPS token, so no stable identity is derived from it.

## Match rule

- `cid 0x010D` + name `^TOYOTA `.
- Named frame → model-level (`vendor: Toyota`, `model` from name); name-null
  frame → vendor/supplier-level (`DENSO TEN (Toyota-group; make unconfirmed)`).
- `stableKey` is MAC-scoped (not payload-derived).

Confidence: HIGH (self-identifying model name + consistent Toyota-group
supplier CID). Parser: `ToyotaVehicleParser` (`toyota_vehicle`).

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x010D` = DENSO TEN Limited.
