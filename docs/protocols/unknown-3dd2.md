# Unknown BLE Emitter — Vanity CID 0x3DD2

## Overview

A previously-uncatalogued BLE emitter using a **vanity-forged** Bluetooth
manufacturer company-ID `0x3DD2` (wire bytes `D2 3D`). The CID is provably
**not assigned by the Bluetooth SIG** — the canonical company-identifiers
registry tops out at `0x10CC` (Linde GmbH) as of June 2026, while `0x3DD2`
is roughly 12,000 IDs above the highest legitimate assignment. The
advertisement carries an SDK-filler tail and an extended-length payload
(~58 bytes), pointing at a bench / pre-production / hobbyist firmware
build.

No public reverse-engineering reference matches this device's payload
fingerprint (exhaustive GitHub / Sourcegraph / grep.app / Theengs decoder
/ OpenMQTTGateway searches returned zero hits). The family is catalogued
here as `vendor: Unknown` so the emitter can be counted and grouped, and
later annotated when a labelled specimen turns up.

## Fingerprint

| Offset (payload, post-CID) | Length | Content | Notes |
|----------------------------|--------|---------|-------|
| 0 | 1 | frame-type marker (`0xC2` or `0x9D`) | Type-A and Type-B co-emit from the same device |
| 0–1 | 2 (LE) | 16-bit running counter | Monotonically decrements ~1 per packet on Type A |
| 2–13 | 12 | sensor / telemetry body | Type A and Type B carry *different* 12-byte bodies |
| 14 (Type A only) | 1 | slow-drift byte (e.g. `e2 → dd`) | Probable RSSI, battery, or temperature reading |
| 26 | 1 | sub-counter / sequence | Decrements ~2 per Type-A frame |
| 27–45 | 19 | **stable identity blob** | `11 02 11 02 3F 30 77 43 AC 00 01 3F 00 34 13 43 77 30 3E` — the device's persistent fingerprint |
| 46–55 | 10 | SDK filler | `06 07 08 09 0A 0B 0C 0D 0E 0F` — textbook Nordic / ESP-IDF / Realtek / Cypress sample-firmware leftover |

The short variant (~29-byte payload) truncates everything past the
device-identity body — legacy-31-byte advertising fallback when the radio
can't fit the full extended frame.

## Identification

- **Primary**: CID `0x3DD2` **plus** the exact 19-byte fingerprint at
  payload offset 27. Either signal alone is *not* sufficient (we don't want
  to claim every random emitter that happens to forge this CID).
- **Frame-type tag**: `0xC2` (Type A) or `0x9D` (Type B) at payload byte 0.
- **Device class**: `unknown`. The signal is "we've seen this same firmware
  before" — not a product identification.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Emission-anomaly flag | CID `0x3DD2` | Not SIG-assigned |
| Stable fingerprint | 19 bytes at payload offset 27 | Same across all observed captures |
| Frame type (A / B) | payload byte 0 | Two distinct frame shapes from one device |
| 16-bit running counter | payload bytes 0–1 LE | Monotonically decrementing |
| SDK-filler presence | trailing 10 bytes | `true` on extended frames, `false` on the 29-byte fallback |
| Raw payload hex | full mfr payload | for forensic inspection |

## What We Cannot Parse

- The vendor / brand / product class — no labelled specimen yet.
- The semantics of the variable mid-bytes (sensor type, channel, units).
- Whether the device is a sensor, asset tag, or proprietary beacon.
- Any cryptographic identity (no recognisable signature/MAC fields).

## Likely Hardware Class

- Payload length (~58 bytes) requires BLE 4.2 / 5.0 extended advertising
  → likely a post-2017 Nordic nRF52 / nRF53, ESP32, Realtek RTL8762, or
  TI CC26xx-class SoC.
- The fact that the firmware shipped with sample-app filler suggests an
  in-development build, a hobbyist project, or a low-cost OEM that didn't
  customise the SDK example beyond what they needed.
- Slow-drift mid-byte + decrementing counter is consistent with a periodic
  environmental sensor or asset tag.

## Stable Identity

Identity is anchored on the **19-byte fingerprint**, *not* the BLE MAC.
CoreBluetooth rotates the BLE MAC, but the firmware-baked fingerprint
remains constant — so multiple "different MAC" sightings can be folded
back into the same logical emitter via `stable_key =
unknown_3dd2_vanity_cid:<fingerprint-hex>`.

## References

- Bluetooth SIG company_identifiers.yaml (canonical) —
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
  (max assigned ID is `0x10CC`; `0x3DD2` is absent)
- Nordic bluetooth-numbers-database (independent mirror) —
  <https://github.com/NordicSemiconductor/bluetooth-numbers-database>
- reelyactive advlib-ble-manufacturers (no handler for `0x3DD2`) —
  <https://github.com/reelyactive/advlib-ble-manufacturers>
- Theengs decoder web tool (no device entry) —
  <https://decoder.theengs.io/>
- Companion vanity-CID anomaly parsers in this codebase:
  - `UnknownECMSharpParser` (CID `0x4345`, "ECM#" prefix)
  - `Unknown3E1D50CDParser` (UUID-only family)
