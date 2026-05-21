# OPPO Plugin

## Overview

**GuangDong Oppo Mobile Telecommunications Corp., Ltd.** is the parent Oppo handset entity, registered to Bluetooth SIG company ID **0x079A**. This CID is distinct from OPPO's sub-brand entries — OnePlus Technology occupies **0x072F**, which is handled by [`OnePlusParser`](./oneplus.md). Devices that emit CID **0x079A** are first-party OPPO hardware (handsets, watches, earbuds, accessories) rather than OnePlus or Realme ecosystem peers.

The vendor attribution for 0x079A is **confidently confirmed** via the canonical Bluetooth SIG `company_identifiers.yaml` registry and Nordic Semiconductor's mirror. The byte-level payload structure, however, is **not publicly documented** and could not be reverse-engineered from a single sustained capture (see "What we know" below). This parser therefore takes the same "vendor-confirmed, payload undocumented" stance as `AmazonHIDRemoteParser`: it confirms the vendor and captures the raw payload bytes for downstream reverse-engineering, without speculating about field semantics.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x079A` (little-endian raw `9a 07`) — GuangDong Oppo Mobile Telecommunications Corp., Ltd. |
| Service UUIDs | absent |
| Local name | absent |
| Sample mfr-data (22 bytes) | `9a07143c067f10039804eed50b1872401f2915030300` |
| Unique emitters | 1 |
| Sightings | 15 (sustained — same device for ~1 minute) |

### Payload bytes (capture from `research/adwatch_export 8.json`, May 2026)

```
9a 07 | 14 3c 06 7f 10 03 98 04 ee d5 0b 18 72 40 1f 29 15 03 03 00
 CID  | 20-byte payload
```

## What we DID figure out

- **Vendor**: GuangDong Oppo Mobile Telecommunications Corp., Ltd. (confirmed against two independent canonical sources).
- **Distinct from OnePlus / Realme**: CID 0x079A is the parent OPPO entity, not the OnePlus sub-brand (0x072F). Existing `OnePlusParser` does NOT match this CID; the two sister parsers cleanly partition the OPPO ecosystem.
- **Payload length is fixed at ~20 bytes in this capture**, with no service UUIDs and no local name in the GAP record — i.e. this is a manufacturer-data-only broadcast, very different from the Heytap/686B service-data emissions used by sibling OnePlus / Realme / OPPO Cross-device peers.

## What we did NOT figure out

- **Field semantics of the 20-byte payload.** No publicly available documentation describes a 0x079A 20-byte advertisement format. Searches across:
  - OPPO developer documentation and ColorOS / HeyTap Spirit cross-device specs
  - `reelyactive/advlib-ble-manufacturers` decoder library
  - Nordic `bluetooth-numbers-database`
  - General BLE reverse-engineering blogs / forums

  …all return nothing actionable for this CID.

- **Speculative patterns visible to the eye** (with too little data to defend):
  - byte 0 `0x14` (decimal 20) matches the remaining payload length — could be a length-prefix.
  - bytes 17-19 `15 03 03` look like a version triplet (e.g. `21.3.3` or `v1.5.3.3`).
  - bytes 8-10 `ee d5 0b` and 13-14 `72 40` could be device-identity or counter fields, but with a single 15-sighting emitter we can't separate static vs. rotating bytes.

  With only **one sustained capture**, we cannot tell which bytes are static identity, which rotate, and which encode state — so the parser deliberately decodes nothing.

- **Product class.** Without a local name, service UUID, or decoded payload, we cannot tell whether the emitter is an OPPO phone, watch, earbud, or accessory. The parser sets `deviceClass = "unknown"`.

## Pipeline registration

Routed by manufacturer-data CID:

```swift
registry.register(parser: OPPOParser(), companyID: 0x079A)
```

## Future work

When a second OPPO capture is observed (different emitter or different time window), diff the 20-byte payloads to identify:
1. Static-identity bytes (same across emitters in the same model)
2. Rotating-counter / state bytes (change over time within one emitter)
3. Per-deployment configuration bytes (vary across emitters but not within one)

That diff is the only path to defensible byte-level decoding without OPPO publishing a spec.

## References

- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — 0x079A = GuangDong Oppo Mobile Telecommunications Corp., Ltd.
- [Nordic Semiconductor bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — mirror confirming 0x079A
- [OPPO Connect (cross-device ecosystem)](https://connect.oppo.com/)
- [OnePlus plugin](./oneplus.md) — sister parser for sibling SIG CID 0x072F
