# eGeeTouch Smart Padlocks (TSA / Luggage / LOTO)

## Overview

eGeeTouch smart padlocks (luggage, TSA, IP45/IP66, LOTO) pair with
**eGeeTouch Manager** (`com.egeetouch.egeetouch_manager`). The advert is a
connectable beacon whose only meaningful field is the **device name, which
embeds the lock's serial number**. No manufacturer or service data is read.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | No manufacturer-data parsing (grep-empty). |
| Service UUID | *(not advertised as key)* | Model-specific lock services `0000fff7`…`0000fffc`, `0000f00d` are GATT-only. |
| Local name | contains `eGeeTouch` (primary, case-sensitive `contains`) or `EGT` (older/alternate) | e.g. `eGeeTouch 12345678` |

### Device-name encoding

| Field | Value |
|---|---|
| Discovery substring | `eGeeTouch` / `EGT` |
| Serial | `name.split("eGeeTouch")[1].trim()` — used by the app as the stable per-lock key (`guest_serial`) |

`EGT` is a short substring and may collide with other names — treat
`EGT`-only matches as low confidence.

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| eGeeTouch lock present | name |
| Serial number | name tail after `eGeeTouch` |

## What Requires GATT Connection

Model (which `fff7`–`f00d` service exists, or DIS `2a24`), serial/firmware
(DIS `2a25`/`2a26`), battery (`180F`/`2A19`), lock state. The GATT channel is
**unencrypted** — the 6-digit passcode is sent in cleartext (active
sniff/replay risk; see `reports/egeetouch-egeetouch_manager.md`).

## Identity Hashing

```
identifier = SHA256("egeetouch:" + serial)[:16]
```

## Detection Significance

Serial broadcast in cleartext → persistent tracking of a specific padlock
(often on luggage, i.e. on a traveller). Name also reveals the device class.

## adwatch Status

No plugin. Future plugin: name contains `eGeeTouch` (or `EGT`), extract the
serial tail.

## References

- apk-ble-hunting `reports/egeetouch-egeetouch_manager_passive.md`
- App code cited: `com/egeetouch/egeetouch_manager/BLEService.java:241,953-954,1025,1049,1102,1105`
