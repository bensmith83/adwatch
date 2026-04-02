# Google Nearby Share / Quick Share BLE Protocol

## Overview

Google Nearby Share (rebranded as Quick Share) allows Android devices to advertise file-sharing availability over BLE. Devices broadcast on service UUID `0xFDF7` to signal that they are ready to receive files or other shared content.

**Important:** UUID `0xFDF7` is shared with Bose audio devices. The parser must disambiguate -- Bose ads include company_id `0x0065` and/or service UUID `0xFE78`, while Nearby Share ads have neither.

## Identifiers

- **Service UUID:** `0xFDF7` (16-bit, assigned to Google LLC)
- **Local name:** Typically absent
- **Company ID:** None in advertisement
- **Device class:** `phone` (default), or derived from device type byte

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFDF7` | Google LLC assigned UUID |
| Local name | (absent) | Nearby Share devices typically do not advertise a name |
| Company ID | (absent) | No manufacturer data in standard Nearby Share ads |

### Disambiguating from Bose

Both Nearby Share and Bose devices use service UUID `0xFDF7`. To distinguish:

| Feature | Nearby Share | Bose |
|---------|-------------|------|
| Company ID | None | `0x0065` (Bose) |
| Service UUID `0xFE78` | Absent | Present |
| Service data on FDF7 | 20+ bytes, version `0x01` | Bose-specific format |
| Local name | Absent | Bose product names |

**Rule:** If company_id == `0x0065` or service UUID `0xFE78` is present, it's Bose. Otherwise, treat `FDF7` service data as Nearby Share.

### Service Data Format (on UUID `0xFDF7`)

Variable length, typically 20+ bytes:

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0 | 1 | Protocol version | `0x01` observed |
| 1-16 | 16 | Encrypted metadata | Device name hash, share target info |
| 17 | 1 | Device capabilities | Bitfield |
| 18 | 1 | Battery / status | Device state |
| 19-22 | 4 | Trailer | Last byte is device type |

### Device Type (last byte of service data)

| Value | Device Type | Device Class |
|-------|-------------|-------------|
| `0x01` | Phone | `phone` |
| `0x02` | Tablet | `tablet` |
| `0x03` | Laptop | `laptop` |
| `0x04` | Watch | `wearable` |
| `0x05` | TV | `tv` |
| `0x06` | Car | `vehicle` |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Protocol version | Service data byte 0 | Typically `0x01` |
| Device type | Service data last byte | Phone, tablet, laptop, etc. |
| Share availability | Presence of FDF7 data | Device is advertising for sharing |

### What We Cannot Parse (encrypted)

- Device name (encrypted in metadata block)
- Account information
- Contact visibility settings
- Specific share capabilities

## Sample Advertisements

```
Android phone (Nearby Share active):
  Service UUID: fdf7
  Service data (fdf7): 01a3b7c4e8f21d6a9053b8e4c7f2a1d50e000000000003

Android tablet:
  Service UUID: fdf7
  Service data (fdf7): 01f8d2a1b6c94e7320a1d8f3b5e6c0a47200000000000200

Android laptop (Chromebook):
  Service UUID: fdf7
  Service data (fdf7): 01c7e5f3a2d8b14960f2c8a7e3d1b59a4100000000000300
```

## Identity Hashing

```
identifier = SHA256("{mac}:{service_data_hash}")[:16]
```

Android devices frequently rotate their BLE MAC address, so identity is unstable across rotations. The encrypted metadata block also rotates periodically.

## Detection Significance

- Indicates an Android device with sharing enabled (common on modern Android phones)
- Device type byte reveals form factor (phone, tablet, laptop, etc.)
- Most of the advertisement is encrypted, limiting passive analysis
- High prevalence in populated areas -- most Android devices broadcast this intermittently

## Parsing Strategy

1. Match on service_uuid `fdf7`
2. Check that company_id is NOT `0x0065` (Bose) and service UUID `fe78` is NOT present
3. Read byte 0 for protocol version
4. Read last byte for device type
5. Map device type to device class
6. Default to `phone` if device type is unknown

## References

- [Bluetooth SIG UUID Database](https://www.bluetooth.com/specifications/assigned-numbers/) -- UUID `0xFDF7` assigned to Google LLC
- [Google Nearby Connections](https://developers.google.com/nearby) -- official documentation
- Community reverse engineering of Nearby Share BLE format
