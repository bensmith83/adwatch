# Yuwell CPAP / APAP ("BreathCare+")

## Overview

Yuwell (China) Pocket / BreathCare / CM100-series APAP & BiPAP machines pair
with **BreathCare+** (`com.yuwell.respirator2`, unobfuscated, Nordic BLE
library). GATT-primary — no telemetry beacon. The only passive signal is the
device-name prefix.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | No manufacturer-data parsing in the app. |
| Service UUID | *(not advertised as discovery key)* | Vendor PAP service `0x5901`, data service `0x5903` are found post-connect. |
| Local name prefix | `BC_PAP` | Pocket/BreathCare BLE models |
| Local name prefix | `Yuwell CM100` | CM100 series |

The prefix gate is `startsWith` in `RespiratorManager.isRequiredServiceSupported`;
other names fall back to a generic `0xFF01` path. Whether a serial follows
the prefix is **unconfirmed**.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor + series | name prefix | `BC_PAP` vs `Yuwell CM100` |
| Candidate serial | name tail | Unconfirmed |

## What Requires GATT Connection

- Treatment data and device SN via notify on `0x5905` (`onTreatmentData` /
  `onDeviceSN`).
- WiFi provisioning via AT commands written to `0x5902`.

## Identity Hashing

```
identifier = SHA256("yuwell_pap:" + mac)[:16]
```

## Detection Significance

A `BC_PAP` / `Yuwell CM100` name reveals a CPAP/APAP nearby — sleep-apnea
medical inference — without connecting.

## adwatch Status

No plugin. A future plugin would match names starting `BC_PAP` or
`Yuwell CM100` (presence-only, medical device class).

## References

- apk-ble-hunting `reports/yuwell-respirator2_passive.md` (Stage 4: `reports/yuwell-respirator2.md`)
- App code cited: `RespiratorManager.java:88-91,100,107,113`; `BleScanner.java:91,131`; `BleService.java:185`
