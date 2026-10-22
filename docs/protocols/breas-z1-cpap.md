# Breas Z1 / Z2 Travel CPAP ("Nitelog")

## Overview

Breas Medical (ex-Human Design Medical / HDM) Z1 Auto / Z2 Auto ultralight
travel CPAPs pair with the **Nitelog / Nitelog 2** app
(`com.breas.nitelog`). The advertisement is identifiable but not readable:
a vendor 128-bit service UUID plus a `Z1`/`Z2` name. The whole command
protocol (opcodes, battery/pressure/AHI, 8-char password login) is GATT,
post-connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | Breas holds no SIG company ID; the app parses no manufacturer data. |
| Service UUID (128-bit) | `f4f2b816-a092-466e-bc76-320462d6341a` | The app's hard `ScanFilter` — primary key. AD vs scan response unconfirmed. |
| Local name | starts with `Z1` or `Z2` | Secondary; the app also does `name.toLowerCase().contains("z1"/"z2"/"breas")` |

The UI replaces the `Z1` token with "breas" for display, so the on-air name
is `Z1…`/`Z2…`.

### Manufacturer / Service Data

None. No manufacturer-specific data and no service-data payload are read;
the service UUID is used as a presence filter only.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor/model family | service UUID / name prefix | "Breas Z1/Z2 CPAP" |
| Model (Z1 vs Z2) | name prefix | |

No serial, firmware, or state is proven to be in the name — Device ID and
firmware are GATT reads (`MSG_GetDeviceID=51`, `MSG_GetFirmwareVersion=55`).
Whether the live name carries a serial tail is a live-capture TODO.

## What Requires GATT Connection

- Battery, pressure, AHI, mode, alarms — behind an 8-char password login
  (`MSG_Bluetooth_LogIn=108`, `MSG_CommsAreLocked=-3`).
- Characteristic UUIDs are **not** hardcoded — resolved at runtime by
  property bits (READ `0x02` / WRITE `0x08`); only the service UUID and CCCD
  `0x2902` are literals.

## Identity Hashing

No stable payload ID; use the MAC:

```
identifier = SHA256("breas_z1:" + mac)[:16]
```

Address type (public/random/RPA) is unconfirmed.

## Detection Significance

- `f4f2b816…` + `Z1`/`Z2` name is a reliable "travel-CPAP user" signal —
  medical (sleep-apnea) inference to any passive observer.
- No serial-in-name leak confirmed; the MAC is the long-lived handle.
- Note `^Z[12]` alone is a weak name match — require the service UUID, or
  treat name-only matches as low confidence.

## adwatch Status

No plugin. A future plugin would match service UUID
`f4f2b816-a092-466e-bc76-320462d6341a` (primary) or name `^Z[12]`
(secondary) and classify as presence-only.

## References

- apk-ble-hunting `reports/breas-nitelog_passive.md` (Stage 4 detail in `reports/breas-nitelog.md`)
- App code cited: `com/breas/nitelog/nitelog/BluetoothLEHelper.java:34` (`FILTER_SERVICE`), `:208` (filter), `:291-316` (`findService`); `com/breas/nitelog/utils/CommonBluetooth.java:229-234`, `:606`
