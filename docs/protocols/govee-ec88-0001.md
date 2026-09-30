# Govee Thermo-Hygrometers: CID-0x0001 Frames on Service 0xEC88

## Overview

Govee's newer thermo-hygrometers (the H5100 / H5101 / H5102 / H5104 /
H5105 / H5108 / H5174 / H5177 family, and some H5075 revisions) do **not**
use Govee's `0xEC88` company ID for their sensor frame. Their
manufacturer-specific data starts with the two bytes `01 00`, which every
BLE stack reads back as **company ID `0x0001`** — a SIG-assigned ID
(Nokia) that Govee does not own, and which TPMS sensors and iBBQ
thermometers also (mis)use. What ties the frame to Govee is the 16-bit
**service UUID `0xEC88`** in the same advertisement and, when present, a
`GVH5xxx_XXXX` local name or Govee's `INTELLI_ROCKS_HW` iBeacon.

Before 2026-09-30 adwatch's `govee` plugin only decoded company IDs
`0xEC88` / `0xEF88`, so these frames fell through to `tpms` (registered on
CID `0x0001`), which invented values such as −37 °C and 0.02 V.

## Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID (as read) | `0x0001` | Really the `01 00` prefix of Govee's payload |
| Service UUID | `0xEC88` | Required (or a Govee local name) — CID 0x0001 alone is ambiguous |
| Local name | `GVH5177_B1E1`, `GVH5102_…` | Usually only in the scan response; often absent |
| iBeacon (optional) | UUID `INTELLI_ROCKS_HW`, major `Pu` / `Qw` | A second manufacturer-data structure (CID `0x004C`) |

## Wire Format

```
01 00 | 01 01 | EE EE EE | BB
└─┬─┘   └─┬─┘   └───┬──┘   └┬┘
 "CID"  prefix   enc24 BE   battery (bits 0-6) + error flag (bit 7)
0x0001  (const)
```

| Offset (post-"CID") | Bytes | Meaning |
|---|---|---|
| 0–1 | `01 01` | Constant prefix (all 56 corpus records) |
| 2–4 | `EE EE EE` | 24-bit big-endian encoded temperature + humidity |
| 5 | `BB` | Battery % in bits 0–6; **bit 7 = sensor error** |
| 6–7 | `00 00` | Only on the 8-byte H5108 variant |

The 6-byte payload is identical to what Home Assistant's
[govee-ble](https://github.com/Bluetooth-Devices/govee-ble/blob/main/src/govee_ble/parser.py)
decodes for the H5100/H5101/H5102/H5103/H5104/H5105/H5174/H5177/H5110/GV5179
family (`decode_temp_humid_battery_error(data[2:6])`, gated on
`msg_length in (6, 8)`), and to the Theengs decoder's
[`H5102_json.h`](https://github.com/theengs/decoder/blob/development/src/devices/H5102_json.h)
(`manufacturerdata` must start `0100`; encoded value at hex offset 8, 6
nibbles; battery at hex offset 14). govee-ble treats CID `0x0001` + an
8-byte payload as the **H5108**, and Theengs publishes no humidity for the
GV5108 (temperature-only probe).

### Decoding the 24-bit value (govee-ble `decode_temp_humid`)

```
base        = (b0 << 16) | (b1 << 8) | b2       # big-endian
negative    = base & 0x800000
value       = base & 0x7FFFFF
temperature = (value // 1000) / 10              # °C, 0.1 resolution
if negative: temperature = -temperature
humidity    = (value % 1000) / 10               # %RH
battery     = BB & 0x7F
error       = BB & 0x80                          # govee-ble reports ERROR
```

This is the same 24-bit encoding the 6-byte `0xEC88` H5072/H5075 frame
uses (see `govee-sensor.md`), just at payload offset 2 instead of 1.

## Worked Examples (NearSight corpus, 2026-09-29)

56 records from 8 devices, all with service UUID `EC88`.

| Manufacturer data | enc24 | Temp | RH | Battery | Notes |
|---|---|---|---|---|---|
| `0100 0101 045b0d 64` | 0x045B0D = 285453 | 28.5 °C | 45.3 % | 100 % | + iBeacon `HWPu` |
| `0100 0101 03d211 56` | 0x03D211 = 250385 | 25.0 °C | 38.5 % | 86 % | + iBeacon `HWQw` |
| `0100 0101 03d5fd 5f` | 0x03D5FD = 251389 | 25.1 °C | 38.9 % | 95 % | same device, named `GVH5177_B1E1` |
| `0100 0101 03a442 4e` | 0x03A442 = 238658 | 23.8 °C | 65.8 % | 78 % | |
| `0100 0101 0734dd 64` | 0x0734DD = 472285 | 47.2 °C | 28.5 % | 100 % | |
| `0100 0101 005460 3b 0000` | 0x005460 = 21600 | 2.1 °C | — | 59 % | 8-byte payload → H5108 (fridge) |
| `0100 0101 0ef0c0 be` | — | — | — | 62 % | **error**: `0xBE` has bit 7 set |

The last row was the "outlier" that decodes to an implausible 97.9 °C /
13.6 %: its battery byte `0xBE` has bit 7 set, which govee-ble treats as a
sensor-error frame (temperature and humidity reported as `ERROR`), leaving
battery `0xBE & 0x7F = 62 %`. The same device sends normal frames
otherwise.

## Model Identification

In order of precedence (adwatch `govee` v1.3):

1. 8-byte payload → **H5108** (govee-ble).
2. Local name `GVH5xxx…` / `Govee…` → `H5xxx`.
3. Govee iBeacon marker (corpus inference, no external reference):

   | iBeacon | Model | Evidence |
   |---|---|---|
   | `INTELLI_ROCKS_HW` + major `Pu` | H5075 | Same marker rides on 6-byte `0xEC88` H5072/H5075 frames |
   | `INTELLI_ROCKS_HW` + major `Qw` | H5177 | Device BD65FB8F sends `HWQw` and also advertises as `GVH5177_B1E1` |

   The iBeacon is a separate AD structure (`4c 00 02 15` + 16-byte UUID
   `494e54454c4c495f524f434b535f4857` = ASCII `INTELLI_ROCKS_HW` + major
   + minor `f2ff` + tx power). Exporters that concatenate
   manufacturer-data structures glue it onto the Govee payload; the parser
   strips it before decoding.
4. Otherwise `unknown`.

## Parser Routing

- `govee`: decodes CID `0x0001` frames only when the advertisement carries
  service UUID `0xEC88` or a Govee local name; payload must be 6 or 8 bytes
  after the iBeacon is stripped.
- `tpms`: declines any frame with service UUID `0xEC88` or a
  `GVH…` / `GV5…` / `Govee…` local name.

## Open Questions

- `HWPu` devices send this 0x0001 frame even though their marker matches
  the H5075; they may be a newer H5075 hardware revision or an H5100-family
  model reusing the marker. Needs a named capture.
- Some unnamed `0xEC88` 6-byte H5075 frames (`88ec 00 040607 00 00`) report
  battery 0 alongside plausible readings; meaning unknown.

## References

- Home Assistant govee-ble `parser.py` (H5100-family branch, `decode_temp_humid_battery_error`, `MIN_TEMP`/`MAX_TEMP`): https://github.com/Bluetooth-Devices/govee-ble/blob/main/src/govee_ble/parser.py
- Theengs decoder `H5102_json.h` (H5100/01/02/04/05/08/74/77): https://github.com/theengs/decoder/blob/development/src/devices/H5102_json.h
- Bluetooth SIG company identifiers (`0x0001` is not Govee's): https://bitbucket.org/bluetooth-SIG/public/src/main/assigned_numbers/company_identifiers/company_identifiers.yaml
- Related: `govee-sensor.md` (0xEC88 / 0xEF88 frames)
