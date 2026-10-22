# Solos AirGo Smart Glasses (AirGo 2 / 3 / Vision, iLens)

## Overview

**Solos** (Solos Technology / Kopin; app `hk.com.solos.airgo`, Capacitor hybrid
with a Kotlin `capacitor_solos_sdk` plugin) has three accessories that are
discovered three different ways:

| Device | Transport | Passive discovery signal |
|--------|-----------|--------------------------|
| AirGo Vision camera | BLE GATT | name prefix `Solos Vision` (+ service `0x180A`) |
| iLens translation display | BLE GATT | name containing `iLens` |
| AirGo 2/3 audio glasses | BT-Classic SPP/RFCOMM | **not BLE-advert discoverable** (one JS device type exposes NUS over BLE — product unconfirmed) |

There is **no manufacturer data and no service data** anywhere.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name prefix | `Solos Vision` | Camera; `DeviceScanner.java:40` (`NAME_PREFIX`). Primary key. |
| Service UUID | `0x180A` (Device Information) | Camera scan filter (`DeviceScanner.java:41,64`). Ubiquitous SIG service — **never attribute on this alone**. |
| Local name substring | `iLens` | iLens; `ILensManager.java:65` (`DEVICE_NAME_KEYWORD`). Sole discriminator. |
| Service UUID | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (NUS) | One audio-glasses device type in the JS dispatcher (MEDIUM); generic Nordic, corroboration only |
| Company ID | — | None |

No serial or firmware is proven to appear in any advertised name.

## What We Can Parse from Advertisements

Device type (camera vs iLens) from the name.

## What Requires GATT

Camera control (`…e5401`), image/data stream (`…e5402` notify), OTA, camera CSR
service `00002760-08c2-11e1-9073-0e8ac72e5450`; iLens translation text (write
`71C4264B-5FEF-9FE1-CF6A-19739BFD9828`). Audio is A2DP/HFP over BT-Classic.

## Identity Hashing

`SHA256("solos:{mac}:{local_name}")[:16]`.

## Detection Significance

`Solos Vision` specifically discloses a **body-worn camera** nearby; `iLens`
discloses AR translation glasses. Audio glasses are visible only to a BR/EDR
inquiry, not a BLE scanner.

## adwatch Status

No plugin; not covered by `smart_glasses.py`. Future match: name prefix
`Solos Vision` or name contains `iLens`. Live-capture TODOs: whether `0x180A` is
in the AD or scan response, the full name shapes, and which product advertises
NUS.

## References

- apk-ble-hunting `reports/solos-airgo_passive.md` (and `reports/solos-airgo.md`)
- Code cited by the report:
  `hk/com/solos/plugins/capacitor_solos_sdk/SDK/bleCamera/DeviceScanner.java`
  (`:40-41`, `:64`), `…/instantTranslate/ilens/ILensManager.java:65`,
  `CameraBleManager.java:46`, `assets/public/chunk-SMONGNFU.js` (SPP dispatcher)
