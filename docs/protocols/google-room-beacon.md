# Google FEA0 Room Beacon Plugin

## Overview

Bluetooth SIG service UUID `0xFEA0` is registered to **Google LLC** (alongside Google's other 16-bit slots — `0xFE2C` Fast Pair, `0xFE9F` Find My Device, `0xFEAA` Eddystone). The SIG registry does not name a sub-product for `0xFEA0`, and no public open-source parser recognizes it: it is absent from the [Eddystone spec](https://github.com/google/eddystone/blob/master/protocol-specification.md), [Nordic's bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/service_uuids.json), and the [reelyactive BLE identifier reference](https://reelyactive.github.io/ble-identifier-reference.html).

The captures we have are consistent with a **Google internal campus / Workspace room-presence beacon** — likely:
- a now-deprecated [Google Beacon Platform / Nearby Notifications](https://hackernoon.com/google-just-killed-android-nearby-notifications-whats-next-for-proximity-marketing-using-beacons-3714d2861e31) deployment (EOL April 2021) repurposed for in-building location, **or**
- a Google Meet hardware room sensor.

The operator-set local name `"Room 8039"` matches Google office building conventions (4-digit room numbers). The vendor product is unconfirmed; the parser is shipped as a "low-confidence Google room beacon".

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFEA0` | SIG-registered to Google LLC. |
| Service data length | 13 bytes | Fixed for the observed `0x03` frame type. |
| Local name | optional, operator-set (e.g. `"Room 8039"`) | Only present in ~50% of captures of the same emitter. |

### Service Data Layout (13 bytes)

```
Byte 0     : 0x03               — frame type / version (constant in all captures)
Bytes 1..7 : fa 8f ca XX XX XX YY — device fingerprint
                                    ├── bytes 1..3 = vendor magic (fa 8f ca, constant)
                                    └── bytes 4..7 = per-emitter device-instance ID
Bytes 8..10: 0x20 0x20 0x20      — fixed-width label slot (3 ASCII spaces in all
                                    observed captures; the user-facing room name
                                    is in the GAP local-name field instead)
Bytes 11..12: bf ff              — constant footer
```

Three distinct emitters observed in 24h differ at bytes 4..7 only — confirming that block is the per-device instance ID.

### Stable Identity

Use the 7-byte fingerprint at offsets 1..7. The iOS `peripheralIdentifier` rotates roughly every ~1h on these emitters, so address-level tracking won't work; the in-payload fingerprint is the only stable handle.

## Detection Significance

- **Google offices.** A cluster of FEA0 / "Room NNNN" advertisements is a strong fingerprint for a Google-occupied building.
- **Anyone with a BLE radio can enumerate rooms.** The room name is broadcast in plaintext as a GAP local name — passive scanning maps the room layout without authentication.
- **No PII in the service data.** The 7-byte fingerprint is opaque and looks vendor-allocated, not a hash of a person's identifier.

## What We Cannot Parse from Advertisements

- The product/manufacturer behind the `0xFEA0` service is unconfirmed. We report `vendor = "Google"` (from the SIG registry) but leave the product as `unconfirmed`.
- The semantics of byte 7 (`0x62`) are not validated; we surface it as part of the fingerprint.

## References

- [Bluetooth SIG member UUIDs (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFEA0 = Google LLC`.
- [Google Nearby Notifications EOL announcement](https://hackernoon.com/google-just-killed-android-nearby-notifications-whats-next-for-proximity-marketing-using-beacons-3714d2861e31).
- [Google Eddystone protocol spec](https://github.com/google/eddystone/blob/master/protocol-specification.md) — FEA0 not listed; this is a different (likely Google-internal) protocol on a sibling UUID.
