# Halliday Smart Glasses + Control Ring (Gyges Labs)

## Overview

**Halliday** (vendor Gyges Labs) DWG smart glasses ship with a companion
**control ring** — two separate BLE peripherals. The app (Flutter,
`gyges_ble` plugin + `flutter_reactive_ble`, with a native Goodix GR SDK for the
ring) scans **broadly** (no `withServices` filter) and matches in Dart by
**device-name prefix** + MAC. Manufacturer data is forwarded to Dart but never
decoded or filtered by company ID, so the **local name is the only
authoritative passive key**.

## BLE Advertisement Format

### Identification

| Peripheral | Signal | Value | Notes |
|-----------|--------|-------|-------|
| Glasses | Local name | contains `Halliday` | App prefix is a runtime value, not a static literal — exact shape (serial tail?) unconfirmed |
| Ring | Local name | `GYGES_Ring_master` or `GYGES_Ring_master_bravechip` (also "Halliday Ring") | Which variant ships on production units is unconfirmed |
| Either | Company ID / service data | — | Not parsed by the app; whether either is present on air is a live-capture TODO |

### Post-connect GATT (not necessarily advertised)

| Peripheral | Services |
|-----------|----------|
| Glasses | Audio `01A6BAAD/AE/AF`, UART `B75497DB/DC/DD`, OTA `e49a25f8/25e0/28e1`, Log `e49a3001/3002/3003` |
| Ring | Goodix GR service `a6ed0401` (TX `a6ed0402` / RX `a6ed0403` / CTRL `a6ed0404`), "GD"/`0x4744`-framed |

The `a6ed0401` Goodix service family is also cited as the Lovense control
service in apk-ble-hunting `lovense-wear_passive.md` (see [lovense.md](lovense.md))
— it is a Goodix SDK service, so it must not be used as a vendor discriminator.

## What We Can Parse from Advertisements

Presence of Halliday glasses and/or the Halliday ring, distinguished by name.

## What Requires GATT

Everything (audio, UART commands, OTA, logs, ring input events).

## Identity Hashing

`SHA256("halliday:{mac}:{local_name}")[:16]`; no serial known in the advert.

## Detection Significance

Wearable-presence signal for a smart-glasses user; the ring name additionally
reveals the companion controller.

## adwatch Status

Not matched by `src/adwatch/plugins/smart_glasses.py` (which covers Meta
CIDs, Snap and Even G1 names). A future match rule: name contains `Halliday`
(glasses) or starts `GYGES_Ring_master` (ring).

## References

- apk-ble-hunting `reports/halliday-glasses_passive.md` (and
  `reports/halliday-glasses.md`, Stage 6d Blutter recovery of `libapp.so`)
