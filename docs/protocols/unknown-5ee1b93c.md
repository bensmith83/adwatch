# Unknown `5EE1B93C-…` BLE Device Plugin

## Overview

A BLE device observed in a 2026-05-20 scan advertising the custom 128-bit service UUID `5EE1B93C-3DF6-11E4-9D9F-164230D1DF67` together with a local name of the form `P` + 7 decimal digits (captured specimen: `P1822176`). **The vendor could not be identified** from public sources. The combination of a globally-unique vendor UUID and a strict `^P\d{7}$` name pattern is specific enough to fingerprint the family without over-matching, so we surface it as a catalog stub for future correlation.

### Observed signature

| Signal | Value |
|---|---|
| Service UUID (128-bit, custom) | `5EE1B93C-3DF6-11E4-9D9F-164230D1DF67` |
| Local name | `P1822176` (matches `^P\d{7}$`) |
| Manufacturer data | none |
| Service data | none |
| Address type | random |
| Capture | `research/adwatch_export 9.json`, 2026-05-20 22:35 UTC, 6 sightings, RSSI -89..-96 dBm |

## BLE Advertisement Format

### Identification

The parser anchors on **both** the full vendor UUID AND a strict anchored name match. Either signal alone is too loose to be safe — 128-bit UUIDs occasionally collide with later-generated random ones, and "letter + 7 digits" is a common SKU shape across many vendors. Requiring both signals avoids false positives.

### Local Name Format

```
P + 7 decimal digits
^P\d{7}$
```

The captured serial `1822176` is captured separately as `metadata.serial` and used as the stable-key anchor.

### Vendor UUID forensics (RFC-4122 v1)

The vendor UUID is a textbook **version-1** UUID — the third group starts with `11e4` (version digit `1`):

| Field | Value | Decode |
|---|---|---|
| time_low / time_mid / time_hi_and_version | `5EE1B93C-3DF6-11E4` | Timestamp ~ **2014-09-29 UTC** (when the developer ran `uuidgen`) |
| clock_seq_hi_and_reserved / clock_seq_low | `9D9F` | 14-bit clock-sequence |
| node | `16:42:30:D1:DF:67` | **Locally-administered MAC** (first-octet bit 1 is set: `0x16 = 0001 0110`) — i.e. NOT a registered IEEE OUI; it is the developer machine's virtual-NIC MAC, not a vendor anchor |

**Cross-corpus correlation:** the same `9d9f-164230d1df67` clock-seq + node tail appears in metadata records of the **MIDAS** ("System of management and protection of mineral resources in Poland") database operated by the Polish Geological Institute / National Research Institute, e.g. record `29bb3786-3e34-11e4-9d9f-164230d1df67`. Those records were minted in late-2014 on the same developer workstation as our BLE UUID, strongly suggesting both came from a developer working in or with a Polish research / government environment in 2014. **We treat this as forensic context only**, since MIDAS is a mineral-resources catalog with no public connection to any BLE product line.

## Stable Key

```
unknown_5ee1b93c:<7-digit-serial>
```

The 7-digit serial in the local name is a stable per-device anchor. A single physical device whose MAC rotates will collapse to one stable key — provided it continues to advertise the same name (which is typical for hardware-burnt serial numbers).

## Detection Significance

- **High-specificity match.** Anchoring on a full 128-bit custom UUID + a strict 8-char name pattern makes false positives very unlikely.
- **Catalog hook.** Surfacing the family now lets us count and group sightings; the parser contract can later be upgraded to attach a real vendor name without breaking downstream consumers, once a labelled specimen turns up.
- **Forensic anchor.** The v1 UUID's timestamp + node bytes are themselves valuable: any future device or codebase sighting the same node tail can be tied back to the same 2014 developer machine.

## Research Leads

All leads dated 2026-05-22. None produced a confident attribution.

| Lead | Outcome |
|---|---|
| Google `"5EE1B93C-3DF6-11E4-9D9F-164230D1DF67"` (literal) | No BLE results. Only hits are Polish MIDAS geological metadata records sharing the same `9d9f-164230d1df67` clock-seq + node tail (e.g. `29bb3786-3e34-11e4-9d9f-164230d1df67`) — forensic correlation but no BLE attribution |
| Google `"5EE1B93C" BLE service UUID` | Generic BLE service-UUID docs only; no product hit |
| Google `"P1822176" BLE device name` | No relevant results |
| Google `"P1822176" device serial number` | No relevant results |
| Google `BLE "P + 7 digit" Polycom / Plantronics / Poly` | Poly/Plantronics serial-number guidance is 6-char alphanumeric, not 7-digit-with-P-prefix. No match |
| Google Pioneer DEH series "P" serial | Pioneer model codes use the prefix in product names (e.g. DEH-S7200BHS), not as a BLE-advertised local name |
| Google Polk Audio MagniFi / React BLE service UUID | No product publishes a matching UUID or naming scheme |
| Google Polish PGI / MIDAS BLE / field-data-collection app | MIDAS is a web-mapping system; PGI's CBDG GeoLOG mobile app exists but has no public BLE protocol that matches |
| Google `5ee1b93c github` | No public code references |
| Google `5EE1B93C-3DF6-11E4 UUID` | UUID-decoder tools only — confirms the v1 timestamp 2014-09-29 |
| IEEE OUI registry `16:42:30` | Not present — locally-administered MAC, expected |
| Google IPL / pet feeder / Mojix / Premier / "PTAGS" with P-prefix | No matches |

## What We Cannot Parse

- **Vendor / model.** No manufacturer data, no service data, no public documentation. The parser is deliberately named `unknown_5ee1b93c` and does NOT invent a vendor.
- **Telemetry.** All payload is presumed to live in GATT characteristics behind the custom service — not in the advertisement.
- **Whether the device is mobile or fixed.** Single-burst capture of 6 sightings over ~9s at -89..-96 dBm (weak, pedestrian distance) is consistent with either a stationary fixture overheard from far away, or a passing carried device.

## References

- `research/adwatch_export 9.json` — 6-sighting capture of the device (deviceIdentifier `3B2C73F2-00D8-7A52-D6B6-79357CC81243`)
- [Sources/Parsers/Unknown5EE1B93CParser.swift](https://github.com/) — the parser implementation
- [Sources/Parsers/Unknown3E1D50CDParser.swift](https://github.com/) — sibling unattributed-family parser (custom-UUID + literal-name gate)
- [Sources/Parsers/UnknownFE7CDAF58E01Parser.swift](https://github.com/) — sibling unattributed-family parser (CID + custom-UUID gate)
- [Sources/Parsers/UnknownECMSharpParser.swift](https://github.com/) — sibling unattributed-family parser (payload-prefix anchor)
- [unknown-3e1d50cd.md](unknown-3e1d50cd.md) — sibling unattributed-family doc
- [unknown-fe7c-daf58e01.md](unknown-fe7c-daf58e01.md) — sibling unattributed-family doc
- [unknown-ecm-sharp.md](unknown-ecm-sharp.md) — sibling unattributed-family doc
- RFC 4122 §4.1 (v1 UUID layout) — used to decode the timestamp / node
- IEEE OUI public registry — used to confirm `16:42:30` is not a registered OUI
- [EGDI metadata record sharing clock-seq+node tail](https://metadata.europe-geology.eu/record/basic/29bb3786-3e34-11e4-9d9f-164230d1df67) — forensic-context correlation (Polish MIDAS), no BLE attribution
