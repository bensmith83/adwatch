# RadiaCode-10x Gamma Spectrometer

## Overview

RadiaCode-10x (RadiaCode-101/102/103…) is a pocket scintillation dosimeter /
gamma spectrometer (app `com.almacode.radiacode`). It is
**connection-based**: count rate, dose rate and the 1024-channel spectrum are
streamed only over GATT. The advert carries a vendor service UUID and a model
name — presence only.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | No manufacturer data parsed (pending live capture if some firmware adds one). |
| Service UUID (128-bit) | `e63215e5-7003-49d8-96b0-b024798fb901` | The app's `ScanFilter.setServiceUuid` — primary key. |
| Local name | `RadiaCode` / `RadiaCode-10x` (e.g. demo `RadiaCode-101D`) | Fallback key; no serial/MAC embedded. |

## What We Can Parse from Advertisements

| Field | Source |
|-------|--------|
| RadiaCode present | service UUID / name |
| Model | name |

## What Requires GATT Connection

CPS, dose rate (µSv/h), spectrum — VSFR protocol: write requests to TX
`E63215E6`, length-prefixed responses on RX notify `E63215E7`. No app-layer
auth on GATT (active-attacker concern). Ground truth: the `radiacode` PyPI
library.

## Identity Hashing

```
identifier = SHA256("radiacode:" + mac)[:16]
```

## Detection Significance

Negligible data leak; flags a niche radiation-monitoring device nearby.

## adwatch Status

No plugin. Future presence plugin: service UUID `e63215e5-…` (fallback name
`RadiaCode`).

## References

- apk-ble-hunting `reports/almacode-radiacode_passive.md` (GATT: `reports/almacode-radiacode.md`)
- App code cited: `defpackage/ie.java:238-261` (scan filter), `defpackage/nh.java` (name/UUIDs), `defpackage/vc0.java`
- `radiacode` Python library (PyPI)
