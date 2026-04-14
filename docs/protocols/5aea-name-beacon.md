# 5AEA Name-Field Beacon (Unidentified)

## Status

**Unidentified**, documented here so future packet captures can help attribute
the source. No parser has been written.

## Observation Summary

Captured in the adwatch export from 2026-04-14 01:14 – 02:06 UTC (a 52-minute
window). Each advertisement carries:

- `local_name` only — **no manufacturer data, no service data, no service
  UUIDs**, no TX power
- `address_type` = `random` (BLE random private address)
- RSSI between -63 and -98 dBm (mostly weak, i.e. nearby but not adjacent)
- 71 distinct MAC/name pairs in 52 minutes
- MAC addresses rotate constantly (unique OUI prefixes visible only a few
  times each)

## Local-Name Format

Exactly **29 ASCII characters** per advertisement. Example captures:

```
5AEA00000AM04ZW!@+j76AZRF-C(%
5AEA00000AC)1$W!@-|6afHPF-C)M
5AEA00000AAk=qW!@;t76AZRF-C*E
5AEA000009{^duW!@;97XbiSF-C($
5AEA00000AIe$3W!@-`76AZRF-C(_
```

### Template (by character index)

| Offset | Bytes | Observation |
|-------:|-------|-------------|
| 0-7   | `5AEA0000` | Fixed magic / version prefix |
| 8-9   | `0A` or `09` | Minor version or counter (both values seen) |
| 10-13 | 4 printable-ASCII chars, including punctuation | Appears to be a stable 4-char device ID — the same 4-char block reappears across multiple MACs (e.g. `7+!#` x6, `8%K` x5, `M04Z` x4) |
| 14-16 | `W!@` | Fixed separator |
| 17-25 | 9 printable-ASCII chars, mixed alnum+punct | High entropy — likely a rolling token or encrypted payload |
| 25-27 | `F-C` | Fixed separator |
| 27-28 | 2 printable-ASCII chars | Trailing token — possibly a short MAC / CRC tag |

The total character set used in the variable fields spans `A–Z`, `0–9`, and
`!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~`. That is `base85`-compatible, suggesting a
base85 or Ascii85-like encoding is being applied to a compact binary payload.

### Byte-level interpretation

`5AEA` as ASCII = `0x35 0x41 0x45 0x41`, which is the hex *string*
representation of the two bytes `0x5A 0xEA`. Whether the broadcaster intends
the magic to be read as ASCII or as the quoted hex bytes is unknown.

## Why This Pattern Is Interesting

1. **The entire payload is packed into the local-name field.** Classifiers
   that only inspect manufacturer-data / service-UUID will ignore this
   entirely. This is a common evasion technique.
2. **MAC address rotation + fixed-structure 29-byte ciphertext** is the
   signature of a privacy-preserving rotating-ID scheme (Apple FindMy,
   Google FMD, Samsung SmartTag all follow this pattern — but none of them
   use the local name).
3. **Same 4-char device ID block repeats across multiple rotating MACs**,
   suggesting the device ID survives MAC rotation. Real rotating-ID trackers
   rotate the ID too, so this is more consistent with a fleet of devices each
   advertising its own stable ID while using random addresses.
4. **71 distinct names in 52 min, each seen 1–44 times** — roughly 10-20 real
   emitters with MAC rotation. Consistent with a cluster of nearby fleet
   trackers or a single vehicle / appliance broadcasting frequently.

## Candidate Hypotheses

None confirmed — captured here to aid triangulation.

1. **Proprietary commercial asset-tracking fleet** — Minew, iTag, or similar
   OEM white-label trackers with a custom application protocol. Likeliest.
2. **A vehicle telematics or tire-pressure beacon** using base85 encoding.
3. **A COVID-era or health-check-in system residual** (unlikely at 2026
   density).
4. **A Pebblebee-style "Find" network variant** that encodes into the name
   field for compatibility with phones that block non-approved mfg-data
   UUIDs. (Mostly ruled out — the major Find networks all use mfg-data.)
5. **A deliberately obfuscated hobby / research project.**

## Next Steps

- Capture the full raw BLE advertising PDU (all AD structures, flags byte,
  TX power field if present) — adwatch currently only records the parsed
  `local_name`, so the underlying byte-level structure is not preserved.
- Correlate sightings with physical locations / times of day to see if a
  mobile emitter is involved (e.g. a passing bus, delivery vehicle).
- Try to base85-decode chars 10-28 to see if the resulting bytes have
  recognizable CRC or timestamp structure.

## References

- [Bluetooth Core Spec 5.4, Vol 3 Part C §11 — AD types](https://www.bluetooth.com/specifications/specs/core-specification/)
- [Ascii85 (Wikipedia)](https://en.wikipedia.org/wiki/Ascii85)
