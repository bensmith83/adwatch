# Govee Temperature / Humidity Sensors

## Overview

Govee's BLE thermo-hygrometer line broadcasts plain-text temperature,
humidity, and battery readings in the BLE advertisement, so no GATT
connection is required to log them. adwatch supports the family
through a single parser that auto-detects sub-format from the local
name.

Govee uses two company IDs:

| Company ID | Family            | Decode  |
|------------|-------------------|---------|
| `0xEC88`   | Plaintext sensors | Direct, per-subformat |
| `0xEF88`   | H512x ("Govee 5") | AES-ECB-encrypted, 24-byte payload |

The LED light-strip product line (`0x8843` / `0x8802` / `Govee_HXXXX_*`
local names) is a separate parser — see `govee-led.md`.

## Supported Models

| Model        | Sub-format | Mfr-data length (bytes) | Notes |
|--------------|------------|-------------------------|-------|
| H5072        | h5075      | 8                       | Pocket thermo-hygrometer |
| H5075        | h5075      | 8 (or 33 with iBeacon piggyback) | Classic Govee sensor |
| H5100, H5101, H5102 | h5075 | 8                  | Refreshed H5075 hardware |
| H5074, H5174 | h5074      | 9                       | Older smart-display sensor |
| H5103, H5104, H5105 | h5103 | 10                  | Display thermometer |
| H5177, H5179 | h5177      | 13                      | Smart-display sensor |
| H5181, H5182, H5183 | h5181 | 6–14                | Meat thermometer (multi-probe) |
| H5121, H5122, H5123, H5124, H5125, H5126, H5130 | h512x | 26 (24 payload) | Encrypted sensors |

Model detection runs on the BLE local name, which always includes the
4-digit model number (e.g. `GVH5075_CF71` → `H5075`).

## h5075 Wire Format (real-world capture)

H5075 is the most common Govee sensor and ships with a tight 8-byte
manufacturer-data block. Captured live:

```
Bytes:   88 EC | 00 | 03 BB 2D | 38 | 00
         └─┬─┘  └┬┘   └───┬───┘  └┬┘  └┬┘
          cid   flag   enc24 BE  batt  trailer
```

| Offset (post-cid) | Bytes | Meaning |
|-------------------|-------|---------|
| 0                 | `00`  | Flag byte (always 0x00 observed) |
| 1–3               | `03 bb 2d` | 24-bit big-endian encoded temp + humidity |
| 4                 | `38`  | Battery percent (0–100) |
| 5                 | `00`  | Trailer (always 0x00 observed) |

### Encoded → temperature / humidity

```
encoded = (b1 << 16) | (b2 << 8) | b3       # 24-bit big-endian
is_negative = (encoded & 0x800000) != 0
if is_negative: encoded ^= 0x800000
temperature_c = encoded / 10000.0
if is_negative: temperature_c = -temperature_c
humidity_pct  = (encoded % 1000) / 10.0
```

Worked example from a real capture (`88ec0003bb2d3800`):

```
encoded = 0x03BB2D = 244525
temperature_c = 244525 / 10000        = 24.45 °C
humidity_pct  = (244525 % 1000) / 10  = 52.5 %
battery       = 0x38                  = 56 %
```

### iBeacon piggyback (33-byte form)

Some H5075 firmware revisions append a full Apple-iBeacon block
*after* the 6-byte sensor payload, producing 33-byte manufacturer
data:

```
88EC | 00 03 BB 2D 38 00 | 4C 00 02 15 | <16-byte iBeacon UUID> | <major> | <minor> | <tx>
└┬┘    └────── h5075 ───┘  └─Apple─┘     └─── stamped "INTELLI_ROCKS_HW" in ASCII ───┘
```

The iBeacon UUID literally encodes the ASCII string
`INTELLI_ROCKS_HW` (an internal Govee/ihoment codename). The parser
ignores everything past the first 6 bytes — sensor decoding is
identical whether the iBeacon is appended or not.

### Heuristic for the legacy padded form

A small number of older Govee firmware variants (and historical adwatch
test fixtures) shipped a longer "padded" payload with an extra two
prefix bytes. The parser auto-detects layout: it uses the modern
6-byte decode when the payload is short or starts with the
`00 <non-zero>` flag pattern, and falls back to the legacy
3-prefix-bytes decode otherwise. This keeps adwatch compatible with
old captures while correctly decoding live H5075 hardware in 2026.

## h5074 / h5103 / h5177 / h5181 (summary)

| Format | Temp encoding | Humidity encoding | Battery |
|--------|---------------|-------------------|---------|
| h5074  | int16 little-endian / 100, offset 2 | uint16 LE / 100, offset 4 | byte 6 |
| h5103  | 24-bit BE encoded (same algo as h5075), offset 4 | from encoded % 1000 / 10 | byte 7 |
| h5177  | int16 LE / 100, offset 6 | uint16 LE / 100, offset 8 | byte 10 |
| h5181  | up to 6 probe int16 LE / 100 at offsets 2,4,6,… | — (meat probes only) | — |

Real-world captures of those sub-formats are not present in the
adwatch research export at time of writing, so the offsets are
inherited from prior community decoders and should be treated as
provisional until verified against live captures.

## h512x (encrypted)

H5121–H5130 sensors switched to AES-ECB-encrypted payloads in 2023
under company ID `0xEF88`:

```
Offset  Bytes   Meaning
  0-1   xx xx   Header (varies)
  2-5   xx xx xx xx   time_ms (32-bit, little-endian)
  6-21  16 bytes      AES-128-ECB ciphertext
 22-23  xx xx          CRC-CCITT(seed=0x1D0F) of bytes 0..21
```

Decryption:

1. Key = `reverse(time_ms_bytes + 12 zero bytes)`
2. Plaintext = `reverse(AES-128-ECB-decrypt(key, reverse(ciphertext)))`
3. Plaintext fields:
   - `byte[2]` → model_id (e.g. 9 → H5124, 11 → H5126)
   - `byte[4]` → battery percent
   - `byte[5]` → event_code (0 = idle, 1 = vibration, …)

If CRC mismatches, the parser still returns the model name from the
local name but drops the decrypted fields.

## Identity Hashing

```
identifier_hash = SHA256(mac_address)[:16]
```

Govee sensors do **not** rotate their BLE MAC (verified across
multiple-week captures), so the MAC itself is a sufficient identity
key — no extra suffixing required.

## References

- Theengs decoder (cross-vendor BLE decoder): https://github.com/theengs/decoder
- ESPHome `govee_h5075` component: https://esphome.io/components/sensor/bluetooth_proxy.html
- Theengs H5075 spec: https://github.com/theengs/decoder/blob/development/docs/devices/GVH5075.md
- Theengs H512x spec: https://github.com/theengs/decoder/blob/development/docs/devices/GVH512X.md
