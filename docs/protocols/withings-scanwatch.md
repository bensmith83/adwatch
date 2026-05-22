# Withings ScanWatch Smartwatch Plugin

## Overview

[Withings ScanWatch](https://www.withings.com/us/en/scanwatch) is a line of hybrid analog/digital health-tracking smartwatches: the original **ScanWatch** (2020), **ScanWatch 2** (2024), **ScanWatch Light** (2024), and **ScanWatch Horizon**. Unlike the rest of Withings' BLE product line (scales, blood-pressure monitors, sleep trackers), the ScanWatch family advertises **by local name only** — no manufacturer data, no service data, no service UUIDs — and the underlying BD_ADDR is a random/rotating address.

This branch of the Withings parser keys off the local name only. It identifies the watch family from the `ScanWatch[ <variant>]` prefix and surfaces the trailing hex token as a `mac_suffix_hint` for inspection, but does **not** mint a stable identifier — the suffix (1-4 hex digits) collides too easily across devices to use as an identity on its own, and there is nothing else in the advertisement to anchor on.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Local name | `^ScanWatch( 2\| Light\| Horizon)? [0-9A-F]{2,4}$` | E.g. `"ScanWatch 2 D9"`. The hex suffix appears to be the trailing bytes of the current random BD_ADDR. |
| Company ID / mfg data | _absent_ | The ScanWatch family does not advertise manufacturer-specific data. Contrast with Withings scales/BPMs, which embed the paired-host MAC at bytes 2-7 of their manufacturer payload. |
| Service UUID | _absent_ | No FF9x signature UUIDs, no SIG service UUIDs. |
| Service data | _absent_ | |
| BD_ADDR type | random (rotating) | Two consecutive ads from the same physical watch arrive from different MAC addresses. |

### Local Name Format

`ScanWatch[ 2| Light| Horizon] <2-4 hex digit suffix>`

Examples:

| Local name | Model | `mac_suffix_hint` |
|---|---|---|
| `ScanWatch ABC` | `ScanWatch` | `ABC` |
| `ScanWatch 2 D9` | `ScanWatch 2` | `D9` |
| `ScanWatch Light 42F0` | `ScanWatch Light` | `42F0` |
| `ScanWatch Horizon 1A` | `ScanWatch Horizon` | `1A` |

The variant token is optional (a bare `ScanWatch` is the original 2020 model). The trailing hex token is required and matches `[0-9A-F]{2,4}` — at least 2 hex digits, anchored at the end of the name. A bare `ScanWatch 2` with no suffix does **not** match.

## Detection Significance

- **Smartwatch class.** When this branch fires (and the scale/BPM signature UUIDs and `WITH`-marker UUID are absent), the parser emits `deviceClass = "smartwatch"` and `metadata["device_class_hint"] = "smartwatch"`. This is the only Withings device class produced from a name-only match — every other Withings parse path lands in `medical`.
- **No stable identity.** `stableKey` is `nil`. The hex suffix is short enough (1-4 nibbles, so up to ~65K combinations) that collisions across nearby watches are plausible, and the BD_ADDR rotates underneath us. A watch seen "again" cannot be confirmed as the same physical unit from advertisement alone.
- **`match_mode = "scanwatch_name"`** is set in metadata so downstream consumers can distinguish name-only ScanWatch hits from scale/BPM hits routed through the same parser.

## What We Cannot Parse from Advertisements

- **A stable per-device identity.** The local-name suffix is too short to be unique, and the underlying BD_ADDR rotates. Re-identifying a specific watch requires an IRK-based resolution by an app that has previously paired with it (see ESPresense discussion below).
- **Heart rate / SpO2 / ECG / activity data.** ScanWatch exposes its health metrics over post-connect GATT characteristics to the Withings Health Mate app; nothing is in the advertisement.
- **Firmware version, battery level.** Standard `0x180A` / `0x180F` services are not present in the advertisement and are negotiated post-connect.
- **Pairing state.** The scales/BPM `provisioning_state` heuristic (`FF…FF` MAC == unprovisioned) does not apply here — there is no manufacturer payload to inspect.

## References

- [Withings ScanWatch 2 support](https://support.withings.com/hc/en-us/sections/16778126045713-ScanWatch-2)
- [Withings ScanWatch 2 teardown](https://www.reverse-costing.com/teardowns/withings-scanwatch-2/)
- [ESPresense discussion #1247 — setting up a ScanWatch with a known IRK](https://github.com/ESPresense/ESPresense/discussions/1247) — confirms rotating BD_ADDR and that pairing relies on IRK rather than a stable MAC.
- [Gadgetbridge issue — Withings ScanWatch reverse engineering](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/3595)
- [Withings developer documentation](https://developer.withings.com/api-reference/) — cloud API only; no public BLE protocol spec.
