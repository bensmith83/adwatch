# Google Play Services (Android BLE Service)

## Overview

Android devices running Google Play Services expose BLE service UUID `0xFCF1`. This is a GATT service used internally by Play Services (likely related to Nearby, Fast Pair, or Find My Device). The service is present on all Android devices with Play Services enabled.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFCF1` | Assigned to Google LLC |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Android device present | service_uuid match | Device with Google Play Services nearby |

### What We Cannot Parse from Advertisements

- Device model or type
- User information
- Play Services version

## Detection Significance

- Indicates an Android device with Google Play Services
- Very common — virtually every Android phone
- Low value for a dedicated plugin given ubiquity
- May appear alongside other Google services (Fast Pair `0xFE2C`, Nearby `0xFEF3`)

## References

- **Bluetooth SIG**: Assigned to Google LLC
- **Issue tracker**: https://issuetracker.google.com/issues/398554946
