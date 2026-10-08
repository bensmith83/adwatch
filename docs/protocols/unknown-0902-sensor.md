# Unknown 0x0902 Environmental Sensor — 29-byte manufacturer frame

## Overview

An unattributed family of BLE sensor beacons that advertise manufacturer
data on Bluetooth SIG company ID `0x0902` with a fixed 29-byte frame: a
6-byte per-unit id, a 5-character uppercase-alphanumeric unit code, and two
slowly varying 16-bit words that read as a temperature / relative-humidity
pair.

The cluster was first analysed on the 2026-08-01 NearSight sweep (110
records / 440 sightings, but only two units — bead adwatch-app-r9yt, parked
on the nearsight-x22 watchlist with the trigger "a second scene or ≥ 3 units
→ an honest cluster parser is defensible"). The 2026-08-25 capture added two
new units on a new date, four in total across two scenes, and the parser
shipped on the 2026-08-26 sweep.

**No vendor is claimed.** `0x0902` is SIG-assigned to *TSC Auto-ID
Technology Co., Ltd.*, a barcode / label-printer maker; nothing about a
sensor-shaped broadcast corroborates that registrant, and one matching
prefix is not an attribution. One of the four unit ids carries an Espressif
OUI (`48:27:E2`), which is consistent with an ESP32-class module but names
no product.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0902` (wire `02 09`) | SIG: TSC Auto-ID Technology Co., Ltd. — uncorroborated |
| Manufacturer payload | exactly 27 bytes after the CID (29 on the wire) | every record in both captures |
| Unit code | bytes 6–10, `[0-9A-Z]{5}` | four distinct codes, two on 08-01 and two on 08-25 (values redacted) |
| Service UUIDs / service data / name | none | |
| Address | random | rotates; the unit id and code do not |

### Byte map (payload offsets, after the 2-byte CID)

| Offset | Field | Size | Observed |
|--------|-------|------|----------|
| 0–5 | unit id | 6 | four distinct 6-byte ids (two on 08-01, two on 08-25; values redacted). Only one, starting `48:27:E2`, is a registered OUI (Espressif); the others are not, in either byte order, so it is reported as an id rather than a MAC |
| 6–10 | unit code | 5 | uppercase alphanumeric ASCII |
| 11–12 | frame type | 2 | `03 07` in both 08-25 units — reported raw |
| 13 | variant | 1 | `81` / `85` — per-unit constant, reported raw |
| 14–15 | reading A | 2 | big-endian; `0a78`, `0a77`, `0b9b` |
| 16–17 | reading B | 2 | big-endian; `0fcb`, `0fc6`, `0e77` |
| 18–26 | tail | 9 | `00 01 80 00 c8 04 00 00 00` / `00 03 40 00 fa 04 00 00 00` — per-unit constants and zero padding, reported raw |

### The two readings (inferred)

The 08-01 analysis found that within one unit **exactly two bytes move
across 100+ records** — one ranging `0x6A–0x74`, the other `0x8E–0xAB` —
and the 08-25 capture shows the same two positions ticking six seconds
apart (`0a78 → 0a77`, `0fcb → 0fc6`). Those are the low bytes of the two
big-endian words at 14–15 and 16–17. Read as ×0.01 fixed point:

| Unit | Reading A | Reading B |
|------|-----------|-----------|
| `<unit-code-1>` (08-25, 02:18 UTC) | 26.80 → 26.79 | 40.43 → 40.38 |
| `<unit-code-2>` (08-25, 02:18 UTC) | 29.71 | 37.03 |

A late-August indoor temperature (°C) and relative humidity (%) pair in the
SHT-style centi-unit scaling many sensor firmwares use, drifting by
hundredths between frames. That is consistent across four units, two dates
and 100+ frames, but no vendor document confirms it — so the parser reports
the values under `inferred_temperature_c` / `inferred_humidity_pct` with
`reading_decode = inferred_be16_x0.01`, and the raw words alongside.

### Examples (real bytes; unit id and unit code redacted)

```
02 09 | xx xx xx xx xx xx | xx xx xx xx xx | 03 07 | 81 | 0a 78 | 0f cb | 00 01 80 00 c8 04 00 00 00
CID     unit id             "XXXXX"          type    var  26.80   40.43   tail

02 09 | yy yy yy yy yy yy | yy yy yy yy yy | 03 07 | 85 | 0b 9b | 0e 77 | 00 03 40 00 fa 04 00 00 00
CID     unit id             "YYYYY"          type    var  29.71   37.03   tail
```

## Parser Scope (passive-only)

`unknown_0902_sensor` claims a frame when the company ID is `0x0902`, the
payload is exactly 27 bytes, and bytes 6–10 are five uppercase-alphanumeric
ASCII characters. The CID alone is deliberately not enough. It reports
`company_id`, `sig_id_status = assigned_uncorroborated`, `sig_id_note`,
`device_id_hex`, `unit_code`, `frame_type_hex`, `variant_hex`,
`inferred_temperature_c`, `inferred_humidity_pct`, `reading_decode`,
`readings_raw_hex`, `tail_hex` and `payload_hex`. No `vendor` key is set.

Identity is keyed on the 6-byte unit id (`unknown_0902_sensor:<id>`), which
survives the random-address rotation; the id and the unit code are both
tagged as unique, stable identifiers. Device class `sensor`.

## What We Cannot Parse

- The vendor or product. Nothing in the frame, the registries, or public
  documentation ties the layout to a name.
- What the `03 07` word, the variant byte and the tail constants mean.
- Whether the readings are exactly °C / %RH — the values fit, the drift
  fits, but it is an inference from ranges, not a decoded spec.

## Detection Significance

- **A stationary environmental sensor.** Four units, each broadcasting a
  fixed id and code from a rotating address, with readings that drift by
  hundredths — the profile of an installed temperature/humidity node, not
  a wearable or a phone.
- **Stable unit id and code.** Both survive address rotation, so a unit is
  re-identifiable across captures; the 5-character code looks like a
  label-printed pairing code.

## References

- NearSight `research/sweep-2026-08-01-candidates.md` — the original cluster analysis (two units, the two moving bytes)
- NearSight `research/sweep-2026-08-26-candidates.md` — the four-unit capture and the reading inference
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0902` = TSC Auto-ID Technology Co., Ltd.
- [nmap `nmap-mac-prefixes`](https://raw.githubusercontent.com/nmap/nmap/master/nmap-mac-prefixes) — `4827E2` = Espressif; the other three ids unregistered
