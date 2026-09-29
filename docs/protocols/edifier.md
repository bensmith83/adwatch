# Edifier Audio BLE Protocol

## Overview

An Edifier audio device (Edifier is an audio maker) observed in the 2026-07-06
sweep with localName `EDIFIER BLE`. The specific model is not broadcast
(generic pairing name), so attribution is brand-level. **Low-trust-sourced.**

## Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x6864` | **pseudo/vanity** (above the SIG ceiling) |
| Service UUID | `1600` | **not a SIG UUID** — Edifier-proprietary 16-bit UUID |
| Local name | `EDIFIER BLE` | brand is load-bearing; also a name-null sibling |
| Manufacturer data | `646876fe7ddf` | payload `76fe7ddf` static across captures |
| Device class | `audio` | |

## Match rule

Route on CID `0x6864` + svc `1600`; in `parse()` require **`1600` OR
`^EDIFIER`** (the pair avoids a lone-vanity-CID false positive). 14 sightings
across two records. Parser: `EdifierAudioParser` (`edifier_audio`).

## References

- Bluetooth SIG `company_identifiers.yaml` / `*_uuids.yaml` — neither `0x6864`
  nor `0x1600` is assigned.
