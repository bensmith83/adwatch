# SEFAM S.Box CPAP ("Sefam Access")

## Overview

SEFAM (France) S.Box / Néa / Ventea / DreamStar CPAP and bilevel devices
pair with **Sefam Access (Lite)** (`com.sefam.sefamaccess`, React Native /
Hermes, `react-native-ble-manager`). The app also bundles the full **iHealth
Device SDK** for a smart scale and pulse oximeter.

For the S.Box itself the only passive signal the app uses is the **device
name**, inferred to be `<serial>-BLE`.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0412` (1042) — SEFAM | SIG-assigned to SEFAM, but **never referenced by the app** (count = 0 in bundle, native libs and Java). Whether the S.Box emits `0x0412` MSD is **unverified — needs a live scan**. |
| Service UUID | *(none known)* | S.Box GATT UUIDs are not present statically in this Lite build. |
| Local name | `<serial>-BLE` | **Inferred** from a pairing help string ("serial number indicated with the `-BLE` suffix"). |

> **Confidence (Stage 5b audit):** downgraded HIGH→MEDIUM. The `-BLE`
> suffix appears exactly once in the bundle, inside user-facing help text;
> **no code constructs, parses or matches** a `<serial>-BLE` name. Treat the
> name format as an inference until confirmed on air.

### Cross-reference: `0x0412` elsewhere in adwatch

[marshall-audio.md](marshall-audio.md) records `0x0412` (SEFAM) as a CID the
scanner sees on Marshall audio adverts and suspects it is non-CID framing
being misread as a company ID. That observation is unrelated to the S.Box;
it means a `0x0412` match alone must **not** be labelled "SEFAM CPAP".

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| SEFAM S.Box (inferred) | name ends `-BLE` | `*-BLE` is generic — low confidence alone |
| Serial (inferred) | name prefix before `-BLE` | PII if confirmed |

## Bundled iHealth accessories

A scanner near the patient may also see the iHealth scale/oximeter (not the
CPAP): standard SIG services Weight Scale `0x181D`, Pulse Oximeter `0x1822`
(chars `2A5E`/`2A5F`/`2A60`), Body Composition `0x181B`, Battery `0x180F`,
DIS `0x180A`; plus iHealth custom services
`636f6d2e-6a69-7561-6e2e-<MODEL>` (ASCII `com.jiuan.<MODEL>`) for HS2S02 /
BFSV22 / BWSV02 / BWSV01 / PO1 / POV11 (MEDIUM, accessory-scoped).

## What Requires GATT Connection

All therapy data, over S.Box GATT UUIDs not recoverable from this build
(runtime / cloud / native provisioned).

## Identity Hashing

```
identifier = SHA256("sefam_sbox:" + serial_from_name)[:16]
```

## Detection Significance

- If confirmed, `<serial>-BLE` broadcasts a globally unique serial in the
  clear: defeats MAC randomization and ties a unique ID to a sleep-apnea
  inference — the most severe-if-true finding of its batch, but
  **evidence-contingent**.
- The 5-minute post-power-on pairing window bounds the app's pairing, not
  necessarily how long the device advertises.

## adwatch Status

No plugin. A future plugin should match `-BLE`-suffixed names only with
corroboration (e.g. a `0x0412` MSD element observed on a live S.Box), since
`*-BLE` is a common generic suffix.

## References

- apk-ble-hunting `reports/sefam-sefamaccess_passive.md` (Stage 4: `reports/sefam-sefamaccess.md`)
- Bundle `@1320645` / byte 1320705 (pairing help string); `it/innove/BleManager.java` (CCCD only); `com/ihealth/communication/base/ble/BleConfig.java` (126 UUIDs)
- adwatch: `src/adwatch/_bt_company_ids.py` (`0x0412: 'SEFAM'`), [marshall-audio.md](marshall-audio.md)
