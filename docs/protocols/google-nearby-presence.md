# Google Nearby Presence (FCF1) BLE Protocol

## Overview
Every Android device running Google Play Services advertises with BLE
service UUID FCF1 for device-to-device presence detection. This is part
of Google's Nearby framework that powers Quick Share, Fast Pair device
discovery, and Find My Device network coordination.

## Manufacturer
**Google LLC** — Mountain View, CA. FCF1 is a Bluetooth SIG-assigned
16-bit UUID registered to Google.

## BLE Advertisement Structure

### Service Data UUID
| UUID | Description |
|------|-------------|
| `FCF1` | Google Nearby Presence service |

### Service Data Format
```
[version:1] [encrypted_payload:20-21]
```

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Version | Observed values: 0x04 |
| 1 | 20-21 | Encrypted payload | Opaque, per-device rotating |

### Advertisement Behavior
- Anonymous: no local name, no manufacturer data
- Payload rotates frequently (privacy measure)
- Present on virtually every Android phone with Play Services enabled
- Multiple distinct ads from the same physical device due to payload rotation
- Typically 21-22 bytes of service data

## Identification
- **Primary**: Service data under UUID `FCF1`
- **Device class**: `phone`
- No meaningful parsing of encrypted payload — identification is presence-only

## Privacy Notes
The encrypted payload rotates to prevent tracking. Individual ads cannot be
correlated to a specific device without Google's key material. The protocol
is intentionally opaque to third parties.

## References
- Bluetooth SIG UUID assignment: FCF1 → Google LLC
- Google Issue Tracker: references to FCF1 in Play Services BLE stack
- Source: `BleGattServerProviderV1.java` in GMS Core Nearby module
