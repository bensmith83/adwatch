# GoPro Plugin

## Overview

Bluetooth SIG company ID `0x02F2` is registered to **GoPro, Inc.**, maker of the Hero / Max action camera line. GoPro cameras advertise continuously while paired or pairable with the GoPro Quik mobile app, using both their proprietary company ID and the SIG-allocated member service UUID `0xFEA6` (the GoPro device service, documented at <https://gopro.github.io/OpenGoPro/ble>).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x02F2` (GoPro, Inc.) |
| Service UUID | `0xFEA6` (GoPro device service) |
| Local name | `"GoPro NNNN"` where `NNNN` is the camera ID printed on the body / used as the Wi-Fi SSID |

Any one of the three is enough to match.

### Manufacturer Data Layout (12 bytes after company ID)

```
Byte 0..1  : frame type / version  (0x02 0x00 in all observed captures)
Byte 2..7  : 6-byte device fingerprint  (rotates with the BD_ADDR — not stable)
Byte 8..11 : trailing state / model identifier
```

The 6-byte fingerprint changes between sightings of the same camera (it tracks the random BD_ADDR), so we surface it as `device_fingerprint` for transient correlation only — it is **not** the right field to key on.

### Service Data 0xFEA6 (8 bytes)

```
Bytes 0..3 : checksum / seed
Bytes 4..7 : ASCII camera ID  (4-digit suffix of the local name)
```

The four trailing ASCII bytes match the four-digit suffix in the local name and the Wi-Fi SSID — this is GoPro's stable per-camera identifier. The parser surfaces it as `camera_id` and uses it as the stable key (`gopro:NNNN`) when present.

## Examples

| Capture | Inference |
|---|---|
| local name `"GoPro 8216"` + FEA6 svc-data `4794973f38323136` | `camera_id = 8216` from both signals (`38 32 31 36` = ASCII `"8216"`) |
| mfg `f20202003e230090fc5e5c44d70f` + UUID `FEA6`, no name | matched on company ID; no stable camera_id available without service data or name |

## References

- [GoPro Open Spec — BLE service definitions](https://gopro.github.io/OpenGoPro/ble)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
