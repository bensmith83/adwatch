# Google FE9F (Undocumented Google BLE Service)

## Overview

Android devices occasionally advertise BLE service UUID `0xFE9F`, which is registered to Google LLC in the Bluetooth SIG 16-bit UUID member range. The exact purpose is undocumented, but it is likely an internal Google/Android system service related to device presence or an older iteration of Nearby services.

This is distinct from:
- `0xFE2C` — Google Fast Pair
- `0xFCF1` — Google Nearby Presence (Play Services)
- `0xFEF3` — Google Nearby Connections
- `0xFEAA` — Eddystone
- `0xFEAF` — Nest/Google Home

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE9F` | Assigned to Google LLC |

### Service Data Layout

Observed payload: 20 bytes, all zeros.

```
Offset  Bytes  Field              Example                                    Notes
------  -----  -----------------  -----------------------------------------  -----------
0-19    20     Unknown            00000000000000000000000000000000000000000   All zeros observed
```

### Observed Payloads

| Service Data (hex)                             | Notes |
|------------------------------------------------|-------|
| `0000000000000000000000000000000000000000`      | 20 bytes, all zeros |

### Key Observations

- Only seen with all-zero payload in our captures
- Appears on random-address Android devices
- Very infrequent — only 1 sighting in 8 hours of scanning
- No manufacturer data or local name accompanies this advertisement
- The 20-byte zero payload may be a placeholder or initialization state

## What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Google/Android device present | Service UUID match | Device running Google services |
| Payload length | Service data | May vary; 20 bytes observed |

## What We Cannot Parse

- Device model or type
- Android version
- Specific Google service purpose
- User information

## Detection Significance

- Indicates an Android device with Google services
- Rare compared to FCF1 (Nearby Presence) and FE2C (Fast Pair)
- May represent an older or deprecated Google BLE service
- Low information density due to all-zero payloads

## References

- **Bluetooth SIG**: UUID `0xFE9F` assigned to Google LLC
- **Related**: See also `google-play-services.md` (FCF1), `fast-pair.md` (FE2C), `google-nearby-share.md` (FDF7)
