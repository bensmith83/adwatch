# iRobot Roomba / Braava BLE Protocol

## Overview

iRobot Roomba and Braava robots advertise BLE primarily during **WiFi
provisioning (setup mode)**. Once paired and on WiFi the robot generally
stops advertising and uses MQTT to the iRobot cloud — so a typical home
will only see these adverts during initial setup or after a factory reset,
plus any fleet of just-unboxed robots in a retail / warranty context.

A second service UUID (Robot Control Command) has been observed on a
non-setup-mode robot in the wild — that path is documented below.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01A8` | **Shared with Mammotion** — magic-byte disambiguation required |
| Mfr-data magic | `A8 01 ?? 31 10` | Parsed by the Home app from raw AD bytes |
| Service UUID (provisioning) | `0bd51777-e7cb-469b-8e4d-2742f1ba77cc` | "Altadena Robot Comm Service" — setup mode |
| Service UUID (control) | `c74edd21-763c-4e54-85a8-43bb75035d75` | "Robot Control Command" — observed live |
| Local names | `Altadena`, `iRobot Braav`, `iRobot Braava`, `Roomba` | Hash-set match (typo `Braav` is in the app) |

The `c74edd21-…` UUID is in the iRobot Home APK's `libcore_jni.so` strings
adjacent to the `c74e0001`-`c74e001d` characteristic family. Both UUIDs
should be treated as iRobot.

## Ad Formats

### Provisioning Mode (per `apk-ble-hunting/reports/irobot-home_passive.md`)

```
Local name: one of {Altadena, iRobot Braav, iRobot Braava, Roomba}
Service UUID (advertised): 0bd51777-e7cb-469b-8e4d-2742f1ba77cc

Manufacturer-data magic (raw AD-byte walk):
  Offset  Bytes        Meaning
    0-1   A8 01        magic short 1 = 0x01A8 (collides with Xiaomi SIG ID)
    2     XX           skip byte
    3-4   31 10        magic short 2 = 0x1031 (product / model tag)
```

The app does not call `getManufacturerSpecificData(int)` — it walks the
raw scan-record bytes and looks for the `01A8 ?? 1031` pattern regardless
of AD-type framing.

### Robot Control Mode (live capture)

```
Service UUID (advertised): c74edd21-763c-4e54-85a8-43bb75035d75
TxPower:                   +9 dBm
No mfr-data, no local-name in observed sample.
```

This UUID gates a separate characteristic family (`c74e0001`–`c74e001d`)
documented in the APK as "Robot Control Command". Likely the connectable
GATT surface used by the app once the robot is past provisioning.

## Mammotion Disambiguation

iRobot and **Mammotion** robotic mowers both use SIG company ID `0x01A8`.
The parser only claims an ad based on CID if the magic `0x31 0x10` follows
at bytes 3–4; otherwise it falls through to Mammotion's parser.

## Parsing Strategy

1. Match if **any** of: name regex, either service UUID, or full magic-byte
   pattern
2. Mfr-data CID alone is insufficient — Mammotion shares it
3. Tag `device_class="vacuum"`

## Identity Hashing

```
identifier = SHA256("irobot:{mac}")[:16]
```

## What We Cannot Parse

- Battery, dustbin status, error codes, mission state — all WiFi/MQTT
- Robot model / serial — only available via post-connect Device Information

## References

- `apk-ble-hunting/reports/irobot-home_passive.md`
- `apk-ble-hunting/targets/irobot-home/r2/libcore_jni.so/unique_uuids_v2.txt`
- Source: combined APK static analysis + live NRF Connect capture (2026-04-26)
