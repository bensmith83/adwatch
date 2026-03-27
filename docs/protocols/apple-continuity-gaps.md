# Apple Continuity — Undocumented/Missing Subtypes

## Overview

The existing `apple_continuity` parser handles known Apple BLE subtypes (company ID `0x004C`). Several subtypes seen in the wild are not currently parsed. This doc covers the gaps.

## Known Subtype Map (furiousMAC/continuity)

| Hex | Name | Status |
|-----|------|--------|
| 0x01 | Unknown | **Not parsed** — undocumented |
| 0x02 | iBeacon | Handled by `ibeacon` parser |
| 0x03 | AirPrint | Not seen in DB |
| 0x05 | AirDrop | Handled by `apple_airdrop` |
| 0x06 | HomeKit | Not seen in DB |
| 0x07 | Proximity Pairing | Handled by `apple_proximity` |
| 0x08 | Hey Siri | Not seen in DB |
| 0x09 | AirPlay Target | Handled by `apple_airplay` |
| **0x0A** | **AirPlay Source** | **BUG: mislabeled as "Hey Siri Variant" in code** |
| 0x0B | Magic Switch | Not seen in DB |
| 0x0C | Handoff | Handled by `apple_continuity` |
| 0x0D | Tethering Target | Not seen in DB |
| 0x0E | Tethering Source | Not seen in DB |
| 0x0F | Nearby Action | Handled by `apple_nearby_action` |
| 0x10 | Nearby Info | Handled by `apple_continuity` |
| 0x12 | Find My | Handled by `apple_findmy` |
| **0x16** | **Unknown** | **Not parsed** — undocumented, labeled "Tethering Source Alt" in code |

## Bugs to Fix

### 1. Subtype 0x0A mislabeled as "Hey Siri Variant"

**File**: `src/adwatch/parsers/apple_continuity.py`

Subtype `0x0A` is **AirPlay Source** (device streaming content TO an AirPlay receiver), not a Hey Siri variant. The real Hey Siri is only `0x08`. This should be relabeled and ideally routed to the `apple_airplay` parser or handled as a recognized AirPlay Source subtype.

### 2. Subtype 0x01 — Unknown

Seen 4 times in DB. Completely undocumented in furiousMAC research. Could be a legacy type or very new. Best approach: recognize and label as `apple_unknown_0x01`, log the payload for future analysis.

### 3. Subtype 0x16 — Unknown

Most common unparsed Apple subtype (27 ads in DB). Also undocumented. Labeled `TETHERING_SOURCE_ALT_TYPE` in code but this is speculative. Best approach: recognize and label as `apple_unknown_0x16`, log payload.

## What to Fix

1. Rename `0x0A` from "Hey Siri Variant" to "AirPlay Source" in `apple_continuity.py`
2. Add `0x01` and `0x16` as recognized-but-unknown subtypes that return a ParseResult with `beacon_type="apple_unknown"` and the raw payload for analysis
3. Consider routing `0x0A` to `apple_airplay` parser instead of continuity

## References

- **furiousMAC/continuity**: https://github.com/furiousMAC/continuity
- **hexway/apple_bleee**: https://github.com/hexway/apple_bleee
