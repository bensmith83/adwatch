# Unknown `0xb1cd` Vanity-CID Beacon (Rapid MAC Rotation)

## Overview

A BLE emitter observed in `research/adwatch_export 9.json` (2026-05-21) that broadcasts an **identical 26-byte manufacturer-data payload** while rotating its random MAC sub-second. Across **37 separate stored records** captured in a ~4-second window (2026-05-21T19:40:36Z to 19:40:40Z), every record carries a distinct random MAC but byte-for-byte the same advertisement bytes:

```
cdb171bf997c9d01c0a62ebf48a0be230bb559a9041275a8ce00
```

The first two wire bytes decode as little-endian SIG company identifier `0xb1cd`, which is **above the SIG-assigned range** (the current registry tops out at `0x10C7` as of mid-2026) — definitively vanity-forged / unregistered. The remaining 24 bytes are a high-entropy opaque body. The tight RSSI clustering (-67 to -85 dBm across all sightings, one -999 no-signal outlier) plus the synchronized burst plus the identical payload bytes is the classic fingerprint of a **single stationary physical device** that rotates its random MAC sub-second and re-advertises the same frame.

**Vendor: not attributed.** Web research (May 2026) for the CID, the 6-byte payload prefix, the 4-byte tail, and the co-emitted `B1BB` service-data UUID (see below) returned no public hits. Catalog stub only — the bit-pattern is distinctive enough to fingerprint, but we deliberately do not invent a vendor.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xb1cd` | NOT SIG-assigned (highest assigned CID is `0x10C7`). LE wire bytes `cd b1`. |
| Manufacturer-data total length | 26 bytes | 2-byte CID + 24-byte body. |
| Manufacturer-data body | exactly `71 bf 99 7c 9d 01 c0 a6 2e bf 48 a0 be 23 0b b5 59 a9 04 12 75 a8 ce 00` | High-entropy except trailing `0x00`. |
| Local name | absent | No advertising name. |
| Service UUIDs | absent | No service UUIDs advertised. |
| Address type | random | MAC rotates sub-second. |

### Wire Layout

```
cd b1 | 71 bf 99 7c 9d 01 c0 a6 2e bf 48 a0 be 23 0b b5 59 a9 04 12 75 a8 ce 00
\__ _/  \_________________________  _________________________/
   \/                              \/
 LE CID                       24-byte opaque body
 0xb1cd                       (high-entropy; trailing 0x00 may be a
                              length terminator — unconfirmed)
```

### Observed Sighting (research/adwatch_export 9.json)

| Field | Value |
|---|---|
| First sighting (earliest) | `2026-05-21T19:40:36Z` |
| Last sighting (latest) | `2026-05-21T19:40:40Z` |
| Distinct stored records | 37 (each with a different random MAC) |
| Sum of `sightingCount` across the 37 records | 45 |
| RSSI range | -67 to -85 dBm (one outlier `-999` = no-signal placeholder) |
| Manufacturer-data hex (identical on all 37) | `cdb171bf997c9d01c0a62ebf48a0be230bb559a9041275a8ce00` |
| Address type | random (every record) |
| Co-emitted service-data (B1BB) | present on 18 of 37 records |

### Co-emitted `B1BB` Service Data

18 of the 37 mystery-payload records also carry service data under the 16-bit UUID `B1BB`. The B1BB payloads are **27 bytes** long and **all start with the literal bytes `b1 bb`** (mirroring the UUID), with a different high-entropy 25-byte tail per record. Across the full export, 104 records carry `B1BB` service data (the other 86 don't co-emit the `0xb1cd` manufacturer-data frame); the B1BB-payload prefixes are diverse (e.g. `b1bbe49b`, `b1bb512f`, `b1bb5b1a`, `b1bb9dec`, `b1bb6432`), so each emission carries a unique rotating value rather than a fixed body.

The mirrored "leading bytes = identifier" style on both surfaces (`cd b1` -> CID `0xb1cd` on mfg-data; `b1 bb` -> UUID `B1BB` on service-data) suggests a single SDK broadcasting on both surfaces. **This parser handles only the manufacturer-data side**; a future parser can catalog the B1BB service-data half once we have more samples.

## Detection Significance

- **Sub-second MAC rotation + identical payload.** This is a privacy / anti-correlation design pattern — the same physical device emits a stable advertisement payload while rotating its random MAC faster than the BLE-base 15-minute rotation interval. Devices that exhibit this pattern include some anti-stalking trackers, some crowd-source-locate beacons, and some research / fuzzing implants. We **do not** make an attribution claim, but the cadence is itself a useful signal: anything matching this parser is by construction MAC-uncoordinated and should be excluded from MAC-based dwell counts.
- **Vanity CID above the SIG-assigned range.** `0xb1cd` cannot be claimed by a real SIG member (the assigned-numbers registry only allocates up to `0x10C7`), so any 0xb1cd emission is either an unregistered SDK or a deliberate squat. The 24-byte body match is the load-bearing safeguard against vanity-CID collisions.
- **Catalog hook for later attribution.** When a labelled specimen (or a second distinct bit-pattern under the same CID) appears, the over-fit body match can be relaxed to a fixed-vs-variable-byte mask without changing the public contract.

## Stable Identity

The MAC is useless — it rotates sub-second. The 24-byte body, however, is identical across all 37 sightings, so for at least this scan window the **body bytes themselves are the device signature**. We anchor the stable key on the body hex so the 37 records collapse to a single stable identity:

```
stableKey = "unknown_cdb1:<24-byte-body-as-hex>"
```

This is the same playbook as [`UnknownECMSharpParser`](../../Sources/Parsers/UnknownECMSharpParser.swift), which anchors on its 6-byte payload tail. The trade-off: if a future device emits a different `0xb1cd` body, it will key separately — but our over-fit match also wouldn't claim it, so the contract is self-consistent.

## Research Leads (May 2026)

| Search | Outcome |
|---|---|
| Bluetooth SIG `company_identifiers.yaml` for `0xb1cd` / `0xcdb1` | Not present. Registry tops out at `0x10C7`. |
| GitHub / Google for `0xb1cd`, `0xcdb1`, `cdb1 manufacturer data` | No documented hits. |
| GitHub / Google for the 6-byte payload prefix `cdb171bf997c` | No hits. |
| GitHub / Google for the 4-byte tail `75a8ce00` | No hits. |
| AltBeacon spec (25-byte body) cross-check | Rejected: AltBeacon places `0xbeac` at bytes 2-3 after the CID; our bytes 2-3 are `71 bf`. Not AltBeacon. |
| `B1BB` as a 16-bit SIG service UUID | Not present in the SIG service-UUIDs registry; vanity. |
| Apple FindMy (`FE9F`), Google FMDN (`fcf1`), Samsung SmartThings Find (`FD5A`), Tile (`FEED`) — all crowd-source-locate / anti-tracking ecosystems | None publishes a B1BB or 0xb1cd signature. |
| AirGuard scan rules | AirGuard scans for the four above; doesn't know about `0xb1cd`. |
| DefenderShield / Cloak BLE anti-tracking products | No documented advertising-format publications matching this signature. |

The high-entropy body is *consistent with* an encrypted rotating-pseudonym design (Apple, Google, and Samsung all use one for their trackers), and the sub-second MAC rotation supports that inference, but no documented signature in the published anti-tracking ecosystems matches — so we record the consistency without claiming it.

## What We Cannot Parse

- **Vendor / model.** No publicly documented match. Best path forward: capture a labelled specimen (photograph + OCR the case label) or capture a connected GATT session to read the device-information-service strings.
- **Body semantics.** The 24 body bytes are opaque. The trailing `0x00` may be a length / terminator; the rest is high-entropy and looks consistent with encrypted data or a hash — but we have only one bit-pattern sample, so we cannot distinguish fixed bytes from variable bytes within the body.
- **B1BB service-data side.** The co-emitted 27-byte B1BB service-data payloads are catalogued in this doc but not yet parsed — they need a second sample set with a second SDK fingerprint before we can safely write a separate parser without over-fitting.

## References

- `research/adwatch_export 9.json` — 37 sightings of the captured device, all bursting within ~4 seconds with distinct random MACs and identical 26-byte mfg-data bytes.
- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — verified `0xb1cd` is absent; highest assigned CID is `0x10C7` as of 2026-05.
- [AltBeacon spec](https://github.com/AltBeacon/spec) — checked and ruled out (body[0..1] would need to be `0xbeac`; our bytes are `71 bf`).
- [`Sources/Parsers/UnknownECMSharpParser.swift`](../../Sources/Parsers/UnknownECMSharpParser.swift) — "vanity CID + exact body bytes" exemplar.
- [`Sources/Parsers/Unknown3E1D50CDParser.swift`](../../Sources/Parsers/Unknown3E1D50CDParser.swift) — "vendor unconfirmable, pattern catalogued" exemplar.
- [`Sources/Parsers/UnknownFE7CDAF58E01Parser.swift`](../../Sources/Parsers/UnknownFE7CDAF58E01Parser.swift) — "two co-emitted surfaces, partial signal" exemplar.
