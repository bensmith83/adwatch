# OpenGate (CDSNA_..._OPENGATE) Plugin

## Overview

A BLE device family observed in `research/adwatch_export 8.json` (May 2026) advertising on a proprietary 128-bit service UUID with a `CDSNA_<serial>_OPENGATE` local name. The naming convention — vendor-prefix + numeric serial + behavioural suffix `OPENGATE` — strongly suggests an **access-control device** announcing it is in "open gate" mode. Plausible product categories: automatic gate opener, garage-door controller, or building intercom panel.

## Vendor attribution

**Not conclusively attributed.** The metadata key `vendor` is therefore set to `Unknown — gate/intercom family`, following the convention used by `Unknown3E1D50CDParser`.

What we ruled out / what we found:

- `CDSNA` is not a registered Bluetooth SIG company name (the SIG company-ID list is 16-bit and indexed by manufacturer-data company ID, which this device does not emit). See the [SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/) page.
- The 128-bit service UUID `2456E1B9-26E2-8F83-E744-F34F01E9D701` is **not** in the Nordic [bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database).
- The same UUID surfaces in two unrelated public discussions where it was being emitted by a **u-blox NINA-B31 / OLP425** development module — see [B4X forum thread #97761](https://www.b4x.com/android/forum/threads/ble2-help-please.97761/) and [Nordic DevZone Q&A 114613](https://devzone.nordicsemi.com/f/nordic-q-a/114613/coded-phy-enabled-device-is-unscannable). The simplest reading is that the gate device is an **OEM product built on a u-blox BLE module**: u-blox publishes example projects and reference code that integrators frequently inherit verbatim, including the example service UUID. The UUID therefore identifies the *integrator's* GATT profile (or a u-blox sample they didn't change), not u-blox the vendor.
- Web searches for `"CDSNA OPENGATE"`, `"CDSNA" gate`, and `"CDSNA" intercom` return zero relevant hits across Comelit, CAME, Nice S.p.A., BFT Automation, or other major European gate-automation brands. We deliberately do not invent a vendor.

When a labelled specimen turns up (e.g. an associated phone app, an FCC ID for the MAC OUI, or a vendor decal), the right upgrade path is to overwrite the `vendor` metadata value in this parser.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (128-bit) | `2456E1B9-26E2-8F83-E744-F34F01E9D701` (proprietary) |
| Local name pattern | `^CDSNA_[0-9]+_OPENGATE$`  — e.g. `CDSNA_34060040141_OPENGATE` |
| Manufacturer data | absent |
| Address type | random |

We match if **either** the service UUID is present (case-insensitive) **or** the local name matches the `CDSNA_<digits>_OPENGATE` pattern. Both signals are highly specific:

- The service UUID is a proprietary 128-bit value with no other known emitter outside this family (the u-blox dev-kit appearances above are unrelated devices that happened to ship the same example UUID; in our capture corpus only this gate-style device emits it).
- The local-name pattern has three independent anchors (`CDSNA_` prefix, numeric body, `_OPENGATE` suffix), so it is extremely unlikely to false-positive.

### Serial extraction

The digits between `CDSNA_` and `_OPENGATE` are captured into `metadata["serial"]`. In the observed sighting the serial was `34060040141` (11 digits) — long enough to plausibly be a per-unit hardware serial number rather than a per-deployment label.

### Stable key

- When the serial is known: `opengate:<serial>` (e.g. `opengate:34060040141`).
- When only the service UUID matched (no parseable name): `opengate:<MAC>` as a fallback. We surface the device-class without claiming serial-level identity.

### Device class

`access_control` — covers gate openers, garage controllers, and door-entry intercoms. We intentionally do not narrow further until we have a vendor attribution.

## Examples

| Capture | Inference |
|---|---|
| service UUID + name `CDSNA_34060040141_OPENGATE` | serial = `34060040141`, class = `access_control`, stableKey = `opengate:34060040141` |
| service UUID only | matched on UUID; serial unknown; stableKey = `opengate:<MAC>` |
| name `CDSNA_999_OPENGATE` only | serial = `999`, class = `access_control`, stableKey = `opengate:999` |

## References

- `research/adwatch_export 8.json` — primary capture (22 sightings, single emitter, 2026-05-20)
- [Bluetooth SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/)
- [NordicSemiconductor/bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — UUID not present
- [B4X forum: BLE2 Help Please](https://www.b4x.com/android/forum/threads/ble2-help-please.97761/) — same UUID on u-blox OLP425 dev module
- [Nordic DevZone Q&A #114613](https://devzone.nordicsemi.com/f/nordic-q-a/114613/coded-phy-enabled-device-is-unscannable) — same UUID on NINA-B31 example
- [u-blox NINA-B31 series](https://www.u-blox.com/en/product/nina-b31-series-u-connect) — candidate underlying BLE module
