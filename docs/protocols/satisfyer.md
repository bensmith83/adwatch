# Satisfyer Connect Devices

## Overview

Satisfyer intimate devices (app `satisfyer-connect` in apk-ble-hunting)
advertise continuously while powered. Satisfyer spans **multiple chip
platforms**, so the passive signature varies by model — three service-UUID
families. The app builds real `ScanFilter`s that can key on service UUID, device
name and/or manufacturer data (`qh6.java:54-63`, `a98.java:65-72`).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (128-bit) | `51361600-c5e7-47c7-8a6e-47ebc99d80e8` (+ `51361500-…` / `51361700-…` variants) | Satisfyer-specific — strongest tell |
| Service UUID (128-bit) | `0000d0ff-3c17-d293-8e48-14fe2e4da212` | Realtek-chip models |
| Service UUID (16-bit) | `0xFFD0` / `0xFFF0` | Generic commodity services — low confidence, shared with many modules |
| Company ID | **unknown** | The filter supports `setManufacturerData(id, data, mask)`, so some models likely emit mfr data, but the CID/layout was not resolved from the obfuscated code — needs a live capture |
| Local name | model-specific | No uniform prefix found |

A single Satisfyer rule needs all three UUID families OR'd together.

## What We Can Parse from Advertisements

Presence/brand (from the custom UUID families).

## What Requires GATT

Motor control; battery (`2a19`).

## Identity Hashing

`SHA256("satisfyer:{mac}:{local_name}")[:16]`.

## Detection Significance

**High privacy sensitivity** — a continuously-advertised custom UUID lets any
passive scanner classify an intimate device.

## adwatch Status

No plugin. Future match: `51361600/51361500/51361700-c5e7-47c7-8a6e-47ebc99d80e8`
or `0000d0ff-3c17-d293-8e48-14fe2e4da212`; `FFD0`/`FFF0` only with other
corroboration. Capture raw manufacturer data to resolve the CID. See also
[lovense.md](lovense.md), [we-vibe.md](we-vibe.md), [svakom.md](svakom.md),
[magic-motion.md](magic-motion.md).

## References

- apk-ble-hunting `reports/satisfyer-connect_passive.md`
- Code cited by the report: `qh6.java:54-63`, `a98.java:65-72`
