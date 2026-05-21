# "ECM#" Vanity-Forged Beacon (CID 0x4345)

## Overview

This parser catalogs a BLE emitter advertising under a forged Bluetooth SIG company identifier with an ASCII `"ECM#"` wire prefix — a fingerprint distinctive enough to safely match, but **without** a confident vendor attribution.

The wire bytes decode as little-endian SIG company ID `0x4345`, which is **not** in the SIG's [company-identifiers registry](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) (the registry tops out at `0x10C7` as of mid-2026). The bytes `45 43` were chosen because they spell ASCII `"EC"` — the same vanity-CID forging style we already document for `FPVanityBeaconParser` (CID `0x5046` = `"FP"`).

The manufacturer-data payload begins with ASCII `"M#"` (`0x4D 0x23`), so the full 4-byte wire prefix reads `"ECM#"`. In automotive shop-talk, `"ECM"` stands for **Engine Control Module** — the canonical aftermarket-OBD acronym — and the trailing `#` (number-sign) is a common identifier-prefix convention. The signal is therefore consistent with an aftermarket OBD-II adapter, marine ECM gateway, or industrial-ECM emitter, but we did not find a published-prefix match for any specific brand.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x4345` | NOT SIG-assigned. LE wire bytes `45 43` spell ASCII `"EC"`. |
| Payload prefix (ASCII) | `"M#"` (`4D 23`) | Combined with the CID bytes, the 4-byte wire prefix reads `"ECM#"`. |
| Local name | absent | No advertising name. |
| Service UUIDs | absent | No service UUIDs advertised. |
| Address type | random | MAC is randomised per advertisement window. |

### Manufacturer Data Layout (captured sample, 10 bytes)

```
45 43 4D 23 | 1C 34 F1 1C 0E D0
\____  ___/  \________  ________/
     \/                \/
   "ECM#"          payload tail (6 bytes)
   wire prefix
```

| Offset | Bytes | Field | Notes |
|---|---|---|---|
| 0..1 | `45 43` | Forged SIG CID | LE `0x4345`; ASCII `"EC"`. |
| 2..3 | `4D 23` | ASCII `"M#"` | Completes the `"ECM#"` wire prefix. |
| 4..9 | `1C 34 F1 1C 0E D0` | Payload tail (opaque) | 6 bytes — exactly MAC-address width. Captured as `payload_tail_hex`; serves as the stable-identity anchor (the BLE source MAC rotates on this emitter). |

### Observed sighting (research/adwatch_export 8.json)

| Field | Value |
|---|---|
| First seen | `2026-05-20T00:31:49Z` (8:31 PM EDT 2026-05-19) |
| Last seen | `2026-05-20T00:32:00Z` |
| Sustained for | ~11 seconds |
| Sighting count | 7 |
| RSSI range | -98 to -95 dBm (weak — likely outdoors, parked vehicle, neighbour's garage, etc.) |
| Manufacturer data hex | `45434d231c34f11c0ed0` |
| Address type | random |

## Vendor Attribution

**Unattributed.** Web research (May 2026) for `"ECM#" BLE` / `"ECM#" OBD bluetooth` / `"45434d23"` returned no documented hits. We explicitly checked the well-known aftermarket OBD adapters:

| Brand | "ECM#" prefix documented? |
|---|---|
| BAFX Products ELM327 | No |
| OBDLink (CX / MX+) | No |
| FIXD (already parsed separately as `FixdOBD2Parser`) | No |
| Autophix (already parsed as `AutophixOBD2Parser`) | No |
| Carista | No |
| Cobb AccessPort / EcuTek | No |
| ScanGauge | No |
| Veepeak | No |

The `"ECM#"` prefix is also consistent with marine ECM gateways (Fox Marine, Digital Yacht NavLINK Blue, KUS NGW) and industrial-ECM telemetry, but again none publishes this exact advertising prefix.

We therefore catalog the emitter as:

- `vendor: Unknown`
- `category: obd_adapter`  (best-guess category from the ASCII prefix)
- `device_class: automotive_ecm`
- `sig_id_status: vanity_forged`

This mirrors the [`Unknown3E1D50CDParser`](../../Sources/Parsers/Unknown3E1D50CDParser.swift) playbook: "vendor unconfirmable, pattern catalogued for future correlation."

## Detection Logic

The parser gates on **two** signals simultaneously — the vanity CID alone would be too false-positive-prone (vanity CIDs are by definition unreserved, so anyone could squat on `0x4345`):

1. `companyID == 0x4345`
2. `manufacturerPayload[0..1] == 0x4D 0x23` (ASCII `"M#"`)

The 4-byte `"ECM#"` ASCII wire prefix is the load-bearing signal.

## Stable Identity

The BLE source MAC is randomised, so MAC alone is not a stable identity. Across the 7-sighting capture window the **6-byte payload tail did not change**, suggesting it's a fixed hardware serial or pre-randomisation MAC fragment. We therefore anchor the stable key to the payload tail:

```
stableKey = "unknown_ecm_sharp:<6-byte-tail-as-hex>"
```

This survives MAC rotation and lets the device appear as a single entity across sessions.

## Detection Significance

- **Single-integrator vanity-CID fingerprint.** As with `FPVanityBeaconParser`, the use of an unreserved SIG ID means anyone using `0x4345` + `"ECM#"` is almost certainly the same product family.
- **Low RSSI (-95 to -98 dBm) + automotive-ECM payload + 11-second sighting window** is the classic fingerprint of a vehicle passing through scan range, or a unit operating in a neighbouring garage / driveway. Worth correlating with concurrent automotive captures (`FixdOBD2Parser`, `AutophixOBD2Parser`).

## What We Cannot Parse from Advertisements

- The vendor identity. Best path forward: photograph an emitting unit, OCR the case label, or capture a GATT-connected session to read the device-information-service strings (Manufacturer Name String, Model Number String).
- The semantics of the 6-byte tail. It does not change across the 7-sighting capture window, so it could be a hardware serial, MAC fragment, or factory-set token. We surface it raw as `payload_tail_hex`.

## References

- `research/adwatch_export 8.json` — 7 sightings of the captured device
- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — verified `0x4345` is absent; highest assigned CID is `0x10C7`.
- [`Sources/Parsers/FPVanityBeaconParser.swift`](../../Sources/Parsers/FPVanityBeaconParser.swift) — vanity-CID forging exemplar (`0x5046` = `"FP"`).
- [`Sources/Parsers/Unknown3E1D50CDParser.swift`](../../Sources/Parsers/Unknown3E1D50CDParser.swift) — "vendor unconfirmable, pattern catalogued" exemplar.
- [`Sources/Parsers/FixdOBD2Parser.swift`](../../Sources/Parsers/FixdOBD2Parser.swift), [`Sources/Parsers/AutophixOBD2Parser.swift`](../../Sources/Parsers/AutophixOBD2Parser.swift) — neighbour parsers in the OBD/automotive-ECM space.
