# iBeacon Routing Bug — Fixed (May 2026)

## Status

**Fixed in May 2026.** The fix lives in:

- `Sources/Parsers/TiltParser.swift` — accepts Apple CID in both byte orders
- `Sources/Pipeline/Pipeline.swift` — IBeaconParser / TiltParser / AltBeaconParser registered for CID `0x4C00` in addition to `0x004C`

## Problem (historical, for reference)

The Swift `RawAdvertisement.companyID` property reads bytes 0–1 of the
manufacturer-data block in **little-endian** order — the
spec-mandated wire format. Apple's company ID `0x004C` is therefore
expected to appear as `4C 00` in the byte stream.

A handful of iBeacon clones and Tilt-compatible firmwares emit the
CID in **big-endian** byte order (`00 4C`) — a Bluetooth-spec
violation but a real-world quirk. The LE extractor reads those bytes
as `0x4C00`, which is not a SIG-assigned CID and previously matched
no parser registration.

Result: iBeacon advertisements from those byte-swapped emitters were
silently dropped — `parsed_by` was NULL for all of them.

## Evidence in adwatch May 2026 export

Two unique records with manufacturer-data prefix `00 4C 02 15 ...`,
both byte-identical (357 + 158 = 515 sightings of the same physical
beacon UUID `2686f39c-bada-4658-854a-a62e7e5e8b8d`). All Apple iBeacon
traffic in the export is BE-encoded; no LE-encoded (`4C 00`) Apple
iBeacons were captured.

## Fix Approach

**Two changes:**

1. **Registration**: `IBeaconParser`, `TiltParser`, and
   `AltBeaconParser` are each registered for **both** CIDs `0x004C`
   and `0x4C00`, so the registry routes byte-swapped advertisements
   to the same parser.

2. **In-parser byte check**: `TiltParser` previously rejected anything
   that didn't start with literal `4C 00`. Relaxed to also accept
   `00 4C` as a valid leading-byte pair.

`IBeaconParser` and `AltBeaconParser` did not have a literal-CID
check in their parser bodies — they identify the frame by the
`02 15` (iBeacon) or `BE AC` (AltBeacon) magic bytes at offset 2–3,
which are byte-order independent. So registration alone is enough
for those two.

## Why not normalise at the classifier level?

That would mean every parser that *legitimately* uses CID `0x4C00`
(if any ever surfaces) would receive Apple iBeacon traffic as well.
The targeted per-parser approach keeps Apple-format parsers opt-in
to the byte-swapped synonym and avoids cross-contamination.

## Verification

Tests in:

- `Tests/ParserTests/IBeaconParserTests.swift` — "Parses byte-swapped Apple CID (00 4C ...) — real export capture"
- `Tests/ParserTests/TiltParserTests.swift` — "Parses byte-swapped Apple CID (00 4C) Tilt clone"
- `Tests/ParserTests/AltBeaconParserTests.swift` — "Parses real CID 0x0118 Radius Networks AltBeacon capture" (covers the related any-CID registration)

All three parsers also retain their original LE-form tests, which
continue to pass.
