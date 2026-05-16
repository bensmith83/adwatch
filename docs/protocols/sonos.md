# Sonos Speakers

## Overview

Sonos speakers (Era, Beam, Arc, Move, Roam, One, Port, Sub, Ace
headphones, etc.) advertise continuously over BLE under company ID
`0x05A7` (Sonos, Inc., BT-SIG-assigned). The BLE radio is on
whenever the speaker is powered, so a single passive scan over a
home with Sonos hardware will pick up every device.

The advertisement is identification + presence only — live state
(volume, playback, group membership, queue) lives behind the Sonos
local API and requires either app pairing or the documented Sonos
HTTP API on the LAN.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x05A7` | Sonos, Inc. (BT SIG) |
| Local name | `S<NN> <XXXX> LE` | e.g. `S39 C930 LE` — model code + 4-hex device suffix + `LE` mode marker |

## Wire Format

Long-form frames are **27 bytes after the CID** in real captures:

```
a7 05 | 06 00 12 [model_token] 2a 00 ca [feature_byte] 00 08 \
        00 00 00 00 00 00 00                                 \
        [6-byte device id] [3-byte family marker]
```

Field positions, byte offsets reckoned from the start of the
manufacturer-data payload (i.e. **after** the 2-byte CID):

| Offset (post-cid) | Bytes        | Field |
|-------------------|--------------|-------|
| 0                 | `06`         | header_byte (constant in captures) |
| 1                 | `00`         | reserved |
| 2                 | `12`         | reserved |
| 3                 | varies       | model_token — varies by product family (`0x20`=S39, `0x40`=S38, `0x00`=S19) |
| 4                 | `2A`         | constant |
| 5                 | `00`         | reserved |
| 6                 | `CA`         | constant |
| 7                 | varies       | feature_byte (`0x00` or `0x06` observed) |
| 8–16              | zeros        | padding / reserved |
| 17–22             | 6 bytes      | per-unit device identifier (MAC-like, stable per physical speaker) |
| 23–25             | 3 bytes      | family marker — distinguishes product line (`33 92 E9`=S39, `33 A8 EA`=S38, `33 AF E9`=S19) |

A 17-byte short-form frame also appears (when the speaker has not
yet emitted its device-id tail) — the parser handles it gracefully
by extracting `model_token` and `feature_byte` while skipping
device-id fields.

## Local Name Decoding

```
"S39 C930 LE"
 └┬┘ └─┬─┘ └┬┘
  │   │    └── BLE mode marker (constant)
  │   └────── 4-hex device suffix (last bytes of MAC; per unit)
  └────────── Sonos model code (see table below)
```

### Known model code → product mapping

Community-sourced (Sonos Community forums + support docs):

| Model code | Product |
|------------|---------|
| `S1`  | Play:5 (Gen 2) |
| `S2`  | Beam (early) |
| `S3`  | Move (early) |
| `S6`  | Connect |
| `S9`  | Sub |
| `S11` | Playbar |
| `S12` | One (Gen 1) |
| `S13` | One (Gen 2) |
| `S14` | Beam |
| `S15` | Port |
| `S16` | Move |
| `S17` | Arc |
| `S18` | Roam |
| `S19` | Arc |
| `S22` | One SL |
| `S23` | Roam SL |
| `S27` | Ace (headphones) |
| `S29` | Era 100 |
| `S30` | Era 300 |
| `S33` | Roam 2 |
| `S38` | One SL |
| `S39` | Era / Sub / Arc (gen) |
| `S43` | One SL (S2-app-only refresh) |

Unmapped codes still parse — `model_code` is preserved verbatim
even if `product` is unknown.

## Identity Hashing

```
identifier_hash = SHA256(device_id_hex)[:16]    # when full frame
identifier_hash = SHA256(mac_address)[:16]      # short-form fallback
```

The 6-byte device_id is stable per physical unit and survives BLE
MAC rotation — making it a reliable per-speaker identity even when
the OS rotates the random address.

## Captured Examples

```
S39 C930 LE   mfr=a705 06 00 12 20 2a 00 ca 00 00 08 00 00 00 00 00 00 00 4c876b2f4abe 3392e9
S39 C02C LE   mfr=a705 06 00 12 20 2a 00 ca 00 00 08 00 00 00 00 00 00 00 4c876b2f43a2 3392e9
S39 58B6 LE   mfr=a705 06 00 12 20 2a 00 ca 00 00 08 00 00 00 00 00 00 00 08f5ec4bdb38 3392e9
S38 B35A LE   mfr=a705 06 00 12 40 2a 00 ca 00 00 08 00 00 00 00 00 00 00 3c3b58fe30d4 33a8ea
S19 F7D1 LE   mfr=a705 06 00 12 00 2a 00 ca 06 00 08 00 00 00 00 00 00 00 3c3b58ad745f 33afe9
```

Note the **first 4 bytes of the device_id** are stable per
manufacturing batch (`4c876b2f` recurs across two distinct S39 units)
— probably a vendor OUI prefix. The last 2 bytes are per-unit.

## What We Cannot Parse Without GATT / LAN API

- Track / artist / album metadata (now-playing)
- Volume level
- Group / stereo-pair membership
- Network connectivity state
- Battery (Move / Roam only)
- Trueplay calibration state
- Audio input selection (Beam / Arc HDMI source)

All of those live in the Sonos local control API on the LAN, not the
BLE advertisement.

## References

- Sonos Community model number forum: https://en.community.sonos.com/components-and-architectural-228996/how-to-find-out-the-manufacture-date-of-my-sonos-components-6846597
- Sonos serial-number support: https://support.sonos.com/en-us/article/find-the-serial-number-and-pin-on-your-sonos-products
- BT SIG company ID `0x05A7` → Sonos, Inc.
