# Fullpower Technologies sensor frames (company ID 0x01EF, nameless variant)

## Overview

**Fullpower Technologies, Inc.** holds Bluetooth SIG company ID `0x01EF`.
Fullpower is the biosensing company behind the **Sleeptracker** platform,
licensed into Simmons / Serta / Tempur mattress lines and wearable sensor
products. NearSight's `SleeptrackerParser` has long claimed the *named*
variant of these frames (`localName == "SleepTracker"`); this doc covers
the **nameless 8-byte telemetry variant** that same parser now claims
(v1.1, 2026-09-19 sweep).

12 records / 193 sightings in the 2026-09-19 merged corpus carry the
nameless frame — all captured 2026-09-06 (one record 2026-09-10) at
−76..−100 dBm, i.e. one pass by a single deployment. Nine distinct unit
IDs in one day reads more like a showroom/retail floor than a residence.
Whether the frames come from sleep sensors, adjustable-bed bases, or
another Fullpower-licensed product is not recoverable passively, so no
product is claimed beyond the Fullpower family.

## Supported models

None pinned. The frames name no model. Reported as Fullpower family
hardware with the product left open.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01EF` | SIG → *Fullpower Technologies, Inc.* — the whole attribution |
| Unit ID | 2 bytes at payload `[2..4)` | 9 distinct values across 12 records; two recur across records and sighting bursts (n=67+3, n=87+3) — stable per physical unit |
| Address type | random | |
| Local name | none (this variant) | The named variant advertises `SleepTracker` |
| Device class | `health` | Same class as the named branch |

## Ad Format — 10 bytes total (8-byte payload after the 0x01EF CID)

```
[0]      0x00 (constant)
[1]      variant — 0x20 / 0x21 / 0x24 observed
[2..4)   unit ID (stable per physical unit)
[4..6)   0x3c 0x06 (constant — the structural gate)
[6..8)   state word — 00 2c / 01 1d / 00 29 observed
```

The variant byte and the state word correlate on every record seen so
far: `0x24` units report `01 1d`; `0x20`/`0x21` units report `00 2x`.
Semantics unknown — plausibly mode/occupancy states — reported raw as
`variant_hex` / `state_hex`.

### Parser gate

CID `0x01EF`, manufacturer payload of exactly 8 bytes, `[0] == 0x00`,
`[4..6) == 3c 06`. Checked **before** the parser's legacy name gate —
these frames carry no localName, which is why v1.0 (name-gated) could
never claim them.

## Identity Hashing

```
identifier = SHA256("sleeptracker:{unit_id_hex}")[:16]
stableKey  = "sleeptracker:{unit_id_hex}"     (unit_id_hex tagged uniqueStable)
```

The 2-byte unit ID is read straight out of the payload and is stable per
physical unit, so identity survives BLE address rotation and the parser
is listed on `StableDeviceKey.payloadStableParsers`. (The legacy named
branch keeps its `mac:name` hash — the same mixed-identity posture as
`alivecor`.)

## What We Cannot Parse

- Which Fullpower-licensed product emits these frames
- The meaning of the variant byte or the state word
- Any telemetry beyond presence/state

## Detection Significance

A sighting means **Fullpower-family hardware is within BLE range** —
most plausibly a sleep-tracker-equipped mattress/bed product, given the
company's licensing footprint. The unit ID re-identifies a unit across
sessions.

## Confidence / Attribution

**Vendor: high.** The SIG company ID is the attribution; the frame's
regularity (two constants + structured fields verified across all 12
records) corroborates it as a designed protocol, not CID abuse.

**Product: low / not claimed.** "Sleep / biosensor hardware (probable)"
is as far as a passive capture goes.

**Field semantics: low.** Variant/state are reported raw; only the unit
ID's stability is asserted.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x01EF = Fullpower
  Technologies, Inc.`
- Fullpower / Sleeptracker product documentation (sleeptracker.com) —
  the licensing model behind the product-family reading.
- NearSight `SleeptrackerParser` v1.1
  (`Sources/Parsers/SleeptrackerParser.swift`, extended 2026-09-19) and
  `research/sweep-2026-09-19-candidates.md` — the sweep that identified
  this cluster.
