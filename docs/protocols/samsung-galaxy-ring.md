# Samsung Galaxy Ring

## Overview

The **Galaxy Ring** is managed by the Galaxy Wearable plugin
`com.samsung.android.ringplugin` (v2.2.16.25050851). The plugin never does
first-contact discovery — it connects to an already-bonded MAC supplied by the
Galaxy Wearable host (`com.samsung.android.app.watchmanager`). The only BLE scan
in the plugin is the **auto-switch re-detection scanner**
(`BLEAutoSwitchManager`), which notices when a previously-paired ring comes back
into range.

So what is known is a **scan filter template**, not a decoded broadcast. The
un-paired advertisement shape lives in the host package / firmware and is
deferred.

Related: [galaxy-watch.md](galaxy-watch.md), [samsung-fd69.md](samsung-fd69.md),
[samsung-galaxy-buds.md](samsung-galaxy-buds.md).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0075` (117) — Samsung Electronics Co. Ltd. | `BLEAutoSwitchManager.java:40` (`COMPANY_ID = 117`). Shared across many Samsung products. |
| Manufacturer data template | `01 00 02 00 01 04`, mask `FF FF FF FF FF FF` | `:24-25`, applied `:51-61`. Constant default, **not per-device**. On air: `75 00 01 00 02 00 01 04 …` |
| Per-device override | `AutoSwitchData.scanFilter` | Written to the host registry at pairing; content not derivable from this APK |
| Device address / name | bonded MAC; exact stored `deviceFixedName` (API ≤ 33) | Re-detection only |

The mask constrains only the first 6 payload bytes; a real Galaxy Ring advert may
carry more bytes after them.

### Manufacturer data byte layout

| Offset (after CID) | Field | Size | Decode |
|--------|-------|------|--------|
| 0–5 | auto-switch match template | 6 | opaque; `01 00 02 00 01 04` — **no byte is assigned a meaning** in the plugin |
| 6+ | unknown | — | not constrained by the filter |

## What We Can Parse from Advertisements

Only a binary "a Samsung auto-switch wearable (likely a paired Galaxy Ring) is
advertising for re-connect" signal. Expect false positives across Samsung's
`0x0075` wearable line.

## What Requires GATT

All telemetry — over a SAP handshake + DATA service (`0x1B1B`), FOTA (`0x1B1A`)
and SIG `0x1801`. Whether `0x1B1B`/`0x1B1A` appear in the advert is not
determinable from the plugin.

## Identity Hashing

The template is constant, so per-device identity is MAC-bound:
`SHA256("galaxy-ring:{mac}")[:16]`. Usefulness depends on whether the ring uses
an RPA (unknown).

## Detection Significance

Low from this package: a coarse presence signal, no cleartext serial/model. The
real exposure assessment needs the host-package / firmware advert.

## adwatch Status

No plugin matches CID `0x0075` + `01 00 02 00 01 04` (`samsung_tv.py` and
`samsung_appliance.py` cover other `0x0075` shapes). A future plugin could tag
this prefix as "Samsung auto-switch wearable (Galaxy Ring?)" at low confidence;
next research target is the host APK `com.samsung.android.app.watchmanager`.

## References

- apk-ble-hunting `reports/samsung-android-ringplugin_passive.md` (and
  `reports/samsung-android-ringplugin.md`)
- Code cited by the report:
  `com.samsung.android.hostmanager.connectionmanager.autoswitch.BLEAutoSwitchManager`
  (`:24-25` template/mask, `:40` CID, `:45-100` filter construction, `:140` scan mode)
