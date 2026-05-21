# Unprovisioned IoT Module Plugin

## Overview

Every BLE System-on-Chip ships with reference firmware that includes a default GAP **Complete Local Name** — a placeholder string the SoC vendor expects the OEM to overwrite before flashing production firmware. When that doesn't happen — dev kit running stock firmware, a cloned/abandoned module, a careless OEM build — the placeholder leaks into the air. We see the result as recurring "ghost" advertisements: identical generic names with no other GAP signals, scattered across many unrelated random MAC addresses.

This parser catalogues exactly those broadcasts: bare factory-default local names with **no manufacturer data, no service UUIDs, and no service data**.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | one of the curated factory-default strings (exact match) |
| Manufacturer data | **must be absent** |
| Service UUIDs | **must be empty** |
| Service data | **must be empty** |
| Address type | typically `random` |

The disjointness rule is load-bearing. A device that happens to use one of these names *and* publishes manufacturer data or a service UUID has been provisioned by some stack; the name is no longer the sole signal and a more specific parser owns the device. This parser deliberately refuses to match in that case so it doesn't shadow a real product.

### Curated Default Names

Start small. The current curated set is:

| Name | Length | Evidence |
|---|---|---|
| `0102000000` | 10 decimal digits | 8 distinct emitters across two days (research/adwatch_export 8.json, May 2026) |

Extending the list requires:

1. Multiple unrelated device identifiers emitting the *identical* name in a single capture window (one specimen could be a misconfigured product; many is a default).
2. Each specimen passes the disjointness rule above — bare name, nothing else.
3. A brief check that the candidate isn't a well-known *product* name (e.g. a Withings device that uses a 15-digit serial as its name).

### Why we don't attribute a vendor

Public web/GitHub searches for the literal string `"0102000000"` against Telink, Realtek RTL8762, Bluetrum AC6328, Jieli JL5800, Espressif, Beken, and Nordic SDK references did not turn up an authoritative attribution as of 2026-05-20. We therefore set `vendor = "Unknown"` and capture the exact default name so future research can correlate. This follows the same "no invented vendor" convention used by [`Unknown3E1D50CDParser`](../../Sources/Parsers/Unknown3E1D50CDParser.swift) and [`UnknownTSeriesParser`](../../Sources/Parsers/UnknownTSeriesParser.swift).

Adjacent suspicious-default patterns (e.g. all-zero, other 10-digit numerics) are *not* in the curated list — we'd need capture evidence to claim them, and matching purely on shape would over-match real products (a Withings device named `882350440249905`, an iPad named `iPad (106)`, etc).

## Stable Key

Intentionally `nil`. The name is a class label, not an identity. The MAC rotates (random address). `identifierHash` is derived from the class — multiple captures of this family collapse into a single bucket.

## Examples

| Capture | Inference |
|---|---|
| local name `"0102000000"`, no mfr/svc data | `iot_factory_default`, vendor `Unknown`, stableKey nil |
| local name `"0102000000"` + Apple mfr data `0x4C00…` | **no match** — the device is provisioned (Apple Continuity parser owns it) |
| local name `"0102000000"` + service UUID `180F` | **no match** — battery service is published, parser defers |
| local name `"1234567890"` (uncurated) | no match |
| local name `iPad (106)` | no match |

## References

- `research/adwatch_export 8.json` — 8 captured emitters, two-day window, May 2026.
- [Telink BLE SDK documentation](https://doc.telink-semi.cn/) — example of an SoC vendor SDK whose reference firmware ships with a default GAP name.
- [`Unknown3E1D50CDParser`](../../Sources/Parsers/Unknown3E1D50CDParser.swift), [`UnknownTSeriesParser`](../../Sources/Parsers/UnknownTSeriesParser.swift) — sibling "vendor unknown, but pattern catalogued" parsers in this repo.
- [Nordic bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — no UUID to look up because the advertisement carries no UUIDs.
