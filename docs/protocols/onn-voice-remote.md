# onn. (Walmart) Voice Remote BLE Protocol

## Overview

The voice remote for an **onn.** streaming box (onn. is Walmart's house
electronics brand; the box is a Google TV / Roku-class device). Observed in the
2026-07-06 sweep with localName `LE-onn.Voice BTFM`. **Low-trust-sourced.**

## Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x4DB4` | **pseudo/vanity** (above the SIG ceiling ~0x10E1 — not a real company id) |
| Service UUIDs | `180F` (Battery) + `8BF0` | `0x8BF0` is a non-SIG proprietary control service |
| Local name | `LE-onn.Voice BTFM` | also a name-null sibling frame |
| Manufacturer data | `b44d43810482` | payload `43810482` **fully static** across captures |
| Device class | `remote` | |

## Match rule

Route on CID `0x4DB4`; in `parse()` require **`8BF0` OR the `onn.Voice` name**
(so a lone vanity CID never claims). 54 sightings across two records (36 named
+ 18 name-null). Parser: `OnnVoiceRemoteParser` (`onn_voice_remote`).

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x4DB4` not present (vanity).
