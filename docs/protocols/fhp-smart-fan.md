# FHP Smart Ceiling Fan (vendor beacon)

## Overview

"FHP" smart ceiling fans (vendor unconfirmed) broadcast a single
manufacturer-data frame whose entire body is printable ASCII — a serial
blob — with a "company ID" of `0x4657`. That CID is **not** allocated
by the Bluetooth SIG; it is the little-endian read of the ASCII bytes
`"WF"` (`0x57 0x46` on the wire). The vendor is stuffing its own ASCII
prefix into the company-ID slot rather than registering a real CID.

The same trick is used by Victron Energy with ASCII `"VE"` / CID
`0x4556` — see [`victron-energy.md`](victron-energy.md). The
"ASCII-stuffed-into-CID-slot" pattern is a recurring shortcut for
vendors who want a deterministic broadcast magic without the cost of a
SIG company-identifier allocation.

## Vendor identification

We have not been able to pin down a single brand:

| Clue | Implication |
|------|-------------|
| LocalName prefix `FHP_` | Possibly "Fanimation Home Premium" / "Fan-Home-Pro" — speculative |
| Mfg-data ASCII prefix `WFH` | Strongest hint, but no public product page or APK matches a `WFH<digits>` SKU |
| BT SIG company list | `0x4657` is **not** assigned — confirms the CID is ASCII repurpose |

Candidate brands surveyed (none confirmed): Fanimation, Westinghouse,
Hampton Bay, Hunter Pacific, Carro, Casablanca. The parser records the
vendor as `Unknown (WFH/FHP)`; downstream tooling should treat this as
an unresolved family until we get a second capture from a labelled
device.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x4657` | **Not SIG-registered** — LE-read ASCII `"WF"` |
| First three ASCII chars | `WFH` | Includes the CID bytes; third byte distinguishes from any other `0x4657` traffic |
| Local name | `FHP_<digits>` | Optional; matches the serial tail of the mfg blob |
| Service UUIDs | None observed | — |

### Manufacturer Data Layout (one capture)

Example payload (research/adwatch_export 13.json):

```
hex:   57 46 48 31 30 30 36 30 30 30 35 41 30 32 58 32 34 34 37 30 33 33 31
ascii: W  F  H  1  0  0  6  0  0  0  5  A  0  2  X  2  4  4  7  0  3  3  1
```

Best-effort field decode:

| Offset | Len | Field          | Example | Notes |
|--------|-----|----------------|---------|-------|
| 0      | 3   | vendor_prefix  | `WFH`   | First 3 ASCII chars (CID + 1 byte) |
| 3      | 4   | model_code     | `1006`  | 4-digit model number |
| 7      | 4   | variant_code   | `0005`  | 4-digit variant / SKU |
| 11     | 3   | hw_rev         | `A02`   | Hardware revision marker |
| 14     | 3   | batch_marker   | `X24`   | Manufacturing year / batch (likely "year 24" → 2024) |
| 17     | tail | serial        | `470331`| Per-unit serial — matches the `_470331` in `localName` |

The structural offsets above are inferred from **one** captured device
(both observed records were the same fan). Field labels should be
treated as best-guess until we get a second SKU to compare.

### LocalName

Localname pattern: `FHP_<digits>` where the digits equal the serial
tail of the mfg blob. Captures show:

- Both fields populated (`FHP_470331` + full mfg blob)
- Mfg-only frames (`localName == nil`)
- (Plausibly) LocalName-only frames — the parser accepts these too

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor family | CID `0x4657` | Always identifiable when CID matches and first 3 ASCII chars are `WFH` |
| Serial | Mfg tail or LocalName | Stable per-device identity |
| Model / variant / hw / batch codes | Mfg ASCII | Best-effort; field offsets unverified across SKUs |

### What We Cannot Parse from Advertisements

- Live fan state (speed, on/off, light state)
- Battery / power telemetry
- Vendor / brand name with confidence
- Encryption keys (none present — payload is plaintext ASCII)

## Detection Significance

- Stable per-device serial enables presence tracking across MAC rotation
- Low confidence on vendor — do not present a brand name in UI without
  the "(unverified)" caveat
- Parser is identification-only; no state telemetry is reverse-engineered

## References

- **Bluetooth SIG Company Identifiers** (`0x4657` not assigned):
  https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/
- **Victron precedent** (same ASCII-in-CID trick with `"VE"` / `0x4556`):
  [`victron-energy.md`](victron-energy.md)
- **Capture**: `research/adwatch_export 13.json`
- **Parser**: `Sources/Parsers/FHPSmartFanParser.swift`
- **Tests**: `Tests/ParserTests/FHPSmartFanParserTests.swift`
