# Svakom Personal-Wellness Devices

## Overview

Svakom intimate devices (app package `sva-sva` in apk-ble-hunting; BLE in
`base_ble_library`) are connectable and advertise while powered. The clearest
passive signal is the GAP local name **`SVAKOM`** — the app's name helper
matches exactly that string (`BleDeviceNameHelper.java:83`). No manufacturer- or
service-data parsing exists.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `SVAKOM` (exact) | Constant brand tag, not per-unit |
| Service UUID | `0xFFE0` | Commodity serial-module service — weak, only with the name |
| Service UUID | `0xAE00` ("alex" service) | Secondary control service; may or may not be advertised per model |
| Company ID | — | Not parsed by the app; capture raw if present |

## What We Can Parse from Advertisements

Presence/brand only.

## What Requires GATT

Motor control (via `0xFFE0` / `0xAE00`), device info / manufacturer name
(`180a` / `2a29`).

## Identity Hashing

The name is a fixed brand string, so per-unit identity is MAC-bound:
`SHA256("svakom:{mac}")[:16]` (useful only if the MAC is static).

## Detection Significance

**High privacy sensitivity.** `SVAKOM` unambiguously marks an intimate device,
broadcast while powered; the expected Just-Works control model means passive
detection can escalate to active control.

## adwatch Status

No plugin. Future match: local name == `SVAKOM`, with `0xFFE0`/`0xAE00` as
corroboration only. See also [lovense.md](lovense.md), [we-vibe.md](we-vibe.md),
[satisfyer.md](satisfyer.md), [magic-motion.md](magic-motion.md).

## References

- apk-ble-hunting `reports/sva-sva_passive.md`
- Code cited by the report: `BleDeviceNameHelper.java:83`
