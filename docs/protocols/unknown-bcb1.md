# Unknown Vanity-CID `0xb1bc` Beacon Family (21-byte payload)

## Overview

A multi-device BLE beacon family observed **13 times across 5 distinct CoreBluetooth deviceIdentifiers** in a single ~22-second scan window in `research/adwatch_export 9.json` (2026-05-21 ~16:23 UTC). All emitters share:

- a **vanity-forged company identifier `0xb1bc`** (LE wire bytes `bc b1`),
- a fixed **21-byte manufacturer-data payload** (2 bytes CID + 19 bytes body),
- random address type with sub-window MAC rotation,
- a frequent paired **service-data entry under 16-bit short UUID `B1BB`** (one hex digit below the CID) whose payload also begins with the literal bytes `b1 bb`.

**Vendor unattributed.** Web research (May 2026) for `0xb1bc`, `bcb1`, the literal payload bytes, the paired `B1BB` service UUID, and adjacent IoT / retail / smart-home / asset-tag / offline-finding ecosystems all returned no documented match. The fingerprint is catalogued as a stub so the family can be counted, grouped, and re-annotated once a labelled specimen is identified.

### Sibling: vanity CID `0xb1cd`

This codebase already catalogues a closely-related family, [`UnknownCDB1Parser`](../../Sources/Parsers/UnknownCDB1Parser.swift), gating on **CID `0xb1cd`** (one hex digit off, observed in the same export). That sibling parser also documents a paired `B1BB` service-data entry with the same mirrored-prefix style (`cd b1` → CID; `b1 bb` → service UUID). The fact that *two adjacent vanity CIDs in the same scan environment both pair with the same `B1BB` service-data structure* is strong evidence that both come from a **single SDK / vendor family** — but neither half has been attributable to a published product or repository.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0xb1bc` (LE wire `bc b1`) | NOT SIG-assigned. Highest SIG-assigned CID is `0x10B5` as of 2026-05 (per Nordic `company_ids.json`). |
| Manufacturer-data length | exactly 21 bytes (2 CID + 19 body) | All 13 captures match. |
| Paired service-data UUID | `B1BB` (16-bit short form) | Optional but present on 11 / 13 captures. Payload starts with `b1 bb` and is 25 bytes long. |
| Local name | absent | No advertising name on any sighting. |
| Service UUIDs | absent | No service-UUID list advertised. |
| Address type | `random` | iOS resolves multiple rotating private MACs back to the same `deviceIdentifier` UUID — see "Stable identity" below. |

### Manufacturer-data layout

The 19-byte body is decomposed as `head(9) | mid(5) | tail(5)`. The parser surfaces all three slices in metadata so downstream tools can re-analyse without re-parsing the wire bytes.

```
bc b1 | HH HH HH HH HH HH HH HH HH | MM MM MM MM MM | TT TT TT TT TT
 \_/   \____________  ____________/  \____  ____/    \______  ______/
 CID         head (9 bytes)              mid (5)         tail (5)
```

(The original design brief sketched a 9/5/4 split that summed to 18 bytes, but every observed body is 19 bytes — we widen the tail from 4 to 5 so the slices reconstruct the body exactly.)

#### Captured walkthrough — device `D41BCB24-C00A-BEA9-74CA-50F6E3F3B10B` (6 sightings)

| Wire bytes | head (9) | mid (5) | tail (5) |
|---|---|---|---|
| `bcb1 3b5035bce2447d173e 5966f05f62 1b2985bec3` | `3b5035bce2447d173e` | `5966f05f62` | `1b2985bec3` |
| `bcb1 3b5035bce2447d173e d2e82f5f62 1b2985bec3` | `3b5035bce2447d173e` | `d2e82f5f62` | `1b2985bec3` |
| `bcb1 4796ee51ee5d4fc4ca 27e4a95357 dc22d9b987` | `4796ee51ee5d4fc4ca` | `27e4a95357` | `dc22d9b987` |
| `bcb1 5ef1cf7aab3a4a8907 34709c2dd6 4fdb36eb54` | `5ef1cf7aab3a4a8907` | `34709c2dd6` | `4fdb36eb54` |
| `bcb1 5f36780a3678fbb522 d9e40544ee 236051490f` | `5f36780a3678fbb522` | `d9e40544ee` | `236051490f` |
| `bcb1 a036af161dbad44b09 13772694bb a0aabcf72a` | `a036af161dbad44b09` | `13772694bb` | `a0aabcf72a` |
| `bcb1 d22f02454fc62a91fb 0835ccd1f4 927c720a10` | `d22f02454fc62a91fb` | `0835ccd1f4` | `927c720a10` |

### Cross-device payload collisions (important wrinkle)

The design brief hypothesised that the 9-byte head is a *stable per-device identifier* and the 5-byte mid is the only thing that rolls. **The captured data disagrees with that hypothesis.** Two patterns rule it out:

1. **Within a single CoreBluetooth deviceIdentifier the entire body changes between sightings**, not just the mid slice. The `D41BCB24-…` table above shows 7 completely-different heads across 6 sightings within seconds.
2. **The exact same 21-byte manufacturer payload was observed simultaneously from 2–3 different deviceIdentifiers.** For example, at `16:23:48Z` three distinct `deviceIdentifier` UUIDs (`D41BCB24`, `D749BCC1`, `8444BFE4`) all emit `bcb15ef1cf7aab3a4a890734709c2dd64fdb36eb54` byte-for-byte. A per-device head would never collide across hosts in lockstep.

The most plausible interpretation is that the **manufacturer-data frame as a whole is a rotating broadcast token** — possibly a relayed offline-finding payload, a shared environment / zone beacon, or a mesh-routing packet — not a stable per-device fingerprint. The much more stable signal is the paired `B1BB` service-data payload (see below).

We nevertheless follow the brief's head/mid/tail decomposition in the parser metadata — it is the natural structural split of the wire bytes — and document the wrinkle here.

### Paired `B1BB` service data (the real stable anchor)

11 of the 13 captures carry a service-data entry under 16-bit short UUID `B1BB`. The payload is 25 bytes, starts with the literal bytes `b1 bb`, and **is stable per device across all sightings**:

| deviceIdentifier | B1BB service-data payload |
|---|---|
| `D41BCB24-C00A-BEA9-74CA-50F6E3F3B10B` | `b1bbe49b8af7a5d51083671d70638eecb2d22bfed3b34fffb08111` |
| `D749BCC1-6C61-3892-AE10-8B807ED06C9A` | `b1bb5b1afb6c1bf9ac36b795e627f768b627a234f3d2c6f654b4c2` |
| `8444BFE4-6F07-91D8-964C-F7330333257B` | `b1bb512f900a29cc68d1fec598db47a3f4be988854a0bc11274350` |
| `B3BDEE48-6E68-2F12-E4B9-451D83C09B1D` | `b1bbedfc3875d984003ab6ba392c3d052dae34b19e61584bd22624` |

The mirrored-prefix design (`bc b1` → CID `0xb1bc`; `b1 bb` → service UUID `B1BB`) is the same SDK fingerprint as the sibling `UnknownCDB1Parser` (`cd b1` → CID `0xb1cd`; `b1 bb` → service UUID `B1BB`).

The parser surfaces this payload in metadata as `service_b1bb_hex` when present.

## Detection Logic

The parser gates on two signals simultaneously:

1. `companyID == 0xb1bc`
2. `manufacturerPayload.count == 19` (exact match — all 13 captures are this length)

The non-SIG-assigned CID alone would be too loose a gate (anyone could squat `0xb1bc`); the exact-length requirement tightens the gate to the observed family. If a future variant emits a different body length we will need a body-shape signal (e.g. a fixed prefix or checksum byte) to keep the gate from over-matching squatters.

## Stable Identity

Per the design brief, the parser's `stableKey` is anchored on the 9-byte head:

```
unknown_bcb1:<9-byte head hex>
```

This **does** collapse multiple sightings that share the same head into a single key — but as documented above, the head is not actually a per-device identifier in the captured data: it appears to be a rotating broadcast frame shared across simultaneously-emitting hosts. Downstream tools that need a true per-device anchor should prefer the `service_b1bb_hex` metadata field when it is present, because that payload is stable per `deviceIdentifier` across all observed sightings.

The parser deliberately does NOT use the BLE source MAC as part of the stable key — MAC rotates within the scan window, and CoreBluetooth's resolved `deviceIdentifier` is not exposed in `RawAdvertisement`.

## Vendor Attribution

**Unattributed.** Searches performed (May 2026):

| Source | Result |
|---|---|
| [Nordic `company_ids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/company_ids.json) | `0xb1bc` absent. Highest assigned CID is `0x10B5`. |
| [Nordic `service_uuids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/service_uuids.json) | Neither `B1BB` nor `B1BC` present. |
| Google Find Hub Network (FHN/FMDN) spec | Different fingerprint: service UUID `0xFEAA`, 29- or 41-byte service-data frame, no manufacturer data. Not a match. |
| Apple Find My accessory spec | CID `0x004C` + own framing. Not a match. |
| Samsung SmartTag | CID `0x0078` + service UUID `0xFD5A`. Not a match. |
| Tile | service UUID `0xFEED`. Not a match. |
| IETF DULT accessory-protocol draft | service UUID `15190001-12F4-C226-88ED-2AC5579F2A85`. Not a match. |
| GitHub / web text-search for `0xb1bc`, `bcb1`, `b1bb` + BLE | No documented hits relating to a BLE protocol. |
| GitHub / web text-search for the literal payload bodies | No documented hits. |

The hypothesis space we considered but **could not confirm**:

- **A private / unpublished offline-finding or mesh-relay protocol.** The cross-device payload collisions + the rotating-frame behaviour + the paired stable service-data anchor are all consistent with a crowd-sourced locate or mesh protocol. But no published SDK / product / repository uses `0xb1bc` / `B1BB` for this purpose, and we explicitly DO NOT speculate on a vendor.
- **A non-Apple, non-Google, non-Samsung tracking SDK** (e.g. a regional or industry-vertical equivalent). Likewise plausible but not confirmable.

We therefore catalogue the family as:

- `vendor`: unset (intentionally — must not invent one)
- `device_class`: `unknown`
- `sig_id_status`: `vanity_forged`

This mirrors the [`UnknownECMSharpParser`](../../Sources/Parsers/UnknownECMSharpParser.swift) and [`UnknownCDB1Parser`](../../Sources/Parsers/UnknownCDB1Parser.swift) playbook: "vendor unconfirmable, pattern catalogued for future correlation."

## What We Cannot Parse from Advertisements

- The vendor / SDK identity. Best path forward: photograph an emitting unit, OCR the case label, capture a GATT-connected session to read the Device Information Service strings, or correlate with concurrent captures in known environments.
- The semantics of the head / mid / tail split. The structural decomposition is a best-effort split of the wire bytes; we have no documentation to confirm field boundaries.
- The semantics of the paired `B1BB` 25-byte service-data payload. We surface it raw as `service_b1bb_hex`.

## Detection Significance

- **Multi-device population.** 5 distinct CoreBluetooth `deviceIdentifier`s within a 22-second window is well above the 1-device threshold that usually justifies a catalog stub. The family is present at scale in at least one of the scan environments.
- **Adjacent to a known sibling family.** The `0xb1cd` (`UnknownCDB1Parser`) and `0xb1bc` (this parser) CIDs are one hex digit apart and share the `B1BB` service-data pairing. Cataloguing both lets us flag and group the wider SDK family in future captures.
- **Possible privacy-protocol fingerprint.** The cross-device rotating frames are notable enough to flag for future security / privacy analysis even without a confirmed vendor.

## References

- `research/adwatch_export 9.json` — 13 sightings of the captured family across 5 distinct CoreBluetooth deviceIdentifiers in a ~22-second scan window.
- [NordicSemiconductor/bluetooth-numbers-database — `v1/company_ids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/company_ids.json) — `0xb1bc` not present; highest assigned CID is `0x10B5` as of 2026-05.
- [NordicSemiconductor/bluetooth-numbers-database — `v1/service_uuids.json`](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/service_uuids.json) — neither `B1BB` nor `B1BC` present.
- [`Sources/Parsers/UnknownCDB1Parser.swift`](../../Sources/Parsers/UnknownCDB1Parser.swift) — sibling vanity-CID `0xb1cd` parser with matching `B1BB` service-data pairing.
- [`Sources/Parsers/UnknownECMSharpParser.swift`](../../Sources/Parsers/UnknownECMSharpParser.swift) — "vanity CID + vendor unconfirmable" exemplar.
- [`Sources/Parsers/FPVanityBeaconParser.swift`](../../Sources/Parsers/FPVanityBeaconParser.swift) — original vanity-CID-forging exemplar (`0x5046` = `"FP"`).
- [Google Find Hub Network accessory spec](https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn) — checked and ruled out as a match.
