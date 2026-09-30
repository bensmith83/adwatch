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
| `0x0001`\* | H5100 family (H5100/01/02/04/05/08/74/77) | `01 00 01 01 <enc24> <batt>` on service `0xEC88` — see `govee-ec88-0001.md` |

\* Not a Govee CID: the payload's leading `01 00` is read back as company
ID 0x0001.

The LED light-strip product line (`0x8843` / `0x8802` / `Govee_HXXXX_*`
local names) is a separate parser — see `govee-led.md`.

## Supported Models

| Model        | Sub-format | Mfr-data length (bytes) | Notes |
|--------------|------------|-------------------------|-------|
| H5072        | h5075      | 8                       | Pocket thermo-hygrometer |
| H5075        | h5075      | 8 (or 33 with iBeacon piggyback) | Classic Govee sensor |
| H5100, H5101, H5102 | h5075 (0xEC88) / cid_0001 | 8 | Per govee-ble these send the CID-0x0001 frame (`govee-ec88-0001.md`) |
| H5074, H5174 | h5074      | 9                       | Older smart-display sensor |
| H5103, H5104, H5105 | h5103 | 10                  | Display thermometer |
| H5177, H5179 | h5177      | 13                      | Smart-display sensor |
| H5181, H5182, H5183 | h5181 | 6–14                | Meat thermometer (multi-probe) |
| H5121, H5122, H5123, H5124, H5125, H5126, H5130 | h512x | 26 (24 payload) | Encrypted sensors |

Model detection runs on the BLE local name, which always includes the
4-digit model number (e.g. `GVH5075_CF71` → `H5075`). The name usually
arrives only in the scan response; without it, a 6-byte `0xEC88` payload
is reported as `H5072/H5075` (govee-ble does the same) and a 7-byte one is
decoded with the H5074 layout.

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
| 4                 | `38`  | Battery percent in bits 0–6; bit 7 = sensor error (govee-ble) |
| 5                 | `00`  | Trailer (always 0x00 observed) |

### Encoded → temperature / humidity

```
encoded = (b1 << 16) | (b2 << 8) | b3       # 24-bit big-endian
is_negative = (encoded & 0x800000) != 0
encoded &= 0x7FFFFF
temperature_c = (encoded // 1000) / 10.0    # govee-ble decode_temp_humid
if is_negative: temperature_c = -temperature_c
humidity_pct  = (encoded % 1000) / 10.0
```

(Corrected 2026-09-30: this doc and the plugin used `encoded / 10000`,
which leaks the humidity digits into the temperature — 244525 gave
24.4525 °C where the ".0525" is really the 52.5 % humidity. The value
packs `temp×10` in the upper digits and `RH×10` in the low three, so the
temperature resolution is 0.1 °C, as in Home Assistant govee-ble and the
Theengs `H5072_json.h` decoder.)

Worked example from a real capture (`88ec0003bb2d3800`):

```
encoded = 0x03BB2D = 244525
temperature_c = (244525 // 1000) / 10 = 24.4 °C
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

The iBeacon's 16-byte UUID is exactly `INTELLI_ROCKS_HW`; its 2-byte
*major* carries two more ASCII characters (`Pu` on H5075 captures, `Qw` on
an H5177), surfaced as `ibeacon_marker` (`HWPu`, `HWQw`).

### Correction (2026-09-30): no "legacy padded form"

This section previously described a layout auto-detect with a "legacy"
3-prefix-byte decode. The plugin never implemented it: it always read the
encoded value at payload offset 3 and the battery at 6 and required 7
bytes, so it could not decode a single real 6-byte capture. The plugin now
reads the layout above (offset 1, battery 4), matching govee-ble (6-byte
`0xEC88` payload, `data[1:5]`) and Theengs `H5072_json.h` (hex offsets
6/12). No capture of a padded form exists in the adwatch or NearSight
corpora.

## h5074 / h5103 / h5177 / h5181 (summary)

| Format | Temp encoding | Humidity encoding | Battery |
|--------|---------------|-------------------|---------|
| h5074  | int16 little-endian / 100, offset 1 | uint16 LE / 100, offset 3 | byte 5 |
| h5103  | 24-bit BE encoded (same algo as h5075), offset 4 | from encoded % 1000 / 10 | byte 7 |
| h5177  | int16 LE / 100, offset 6 | uint16 LE / 100, offset 8 | byte 10 |
| h5181  | up to 6 probe int16 LE / 100 at offsets 2,4,6,… | — (meat probes only) | — |

**h5074 verified (2026-09-30).** The table previously gave offsets 2 / 4 /
6. The real 7-byte payload is `00 | temp LE16 | hum LE16 | batt | 02`, per
Home Assistant govee-ble (7-byte `0xEC88` payload, `"<hHB"` at
`data[1:6]`) and Theengs `H5074_json.h` (hex offsets 6 / 10 / 14). NearSight
corpus frame `88ec00fc0dc5086402` (`Govee_H5074_42AC`) decodes to
**35.80 °C / 22.45 % / 100 %** at offset 1, but to −150.9 °C / 256.1 %
(battery 0x02, really the trailer) at offset 2. Eight named H5074 captures
all agree with offset 1.

h5103 and h5177 (on `0xEC88`) remain unverified. govee-ble decodes the
H5103/H5177 family from the CID-0x0001 frame instead (payload offset 2,
see `govee-ec88-0001.md`), and the only named H5177 in the NearSight corpus
(`GVH5177_B1E1`) sends exactly that frame; treat the `0xEC88` h5103/h5177
offsets as provisional.

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

- Home Assistant govee-ble parser: https://github.com/Bluetooth-Devices/govee-ble/blob/main/src/govee_ble/parser.py
- Theengs H5074 / H5072-75 definitions: https://github.com/theengs/decoder/blob/development/src/devices/H5074_json.h , https://github.com/theengs/decoder/blob/development/src/devices/H5072_json.h
- CID-0x0001 H5100-family frames: `govee-ec88-0001.md`
- Theengs decoder (cross-vendor BLE decoder): https://github.com/theengs/decoder
- ESPHome `govee_h5075` component: https://esphome.io/components/sensor/bluetooth_proxy.html
- Theengs H5075 spec: https://github.com/theengs/decoder/blob/development/docs/devices/GVH5075.md
- Theengs H512x spec: https://github.com/theengs/decoder/blob/development/docs/devices/GVH512X.md
