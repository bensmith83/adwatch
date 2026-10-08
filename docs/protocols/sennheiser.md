# Sennheiser MOMENTUM Plugin

## Overview

**Sennheiser** is the German consumer-audio brand behind the **MOMENTUM** family of premium wireless headphones and earbuds. The product line includes:

| Marketing model | Form factor |
|---|---|
| MOMENTUM 4 | Over-ear headphones |
| MOMENTUM True Wireless 3 / 4 | True-wireless earbuds |
| MOMENTUM Sport | Heart-rate-tracking earbuds |
| MOMENTUM Wireless (legacy) | Over-ear headphones |

A bit of corporate history matters for company-ID attribution: Sennheiser's consumer-audio business was spun out of **Sennheiser electronic GmbH & Co. KG** in 2021 and is now operated by **Sonova Consumer Hearing GmbH** (a subsidiary of Swiss hearing-aid maker Sonova) under license to use the Sennheiser brand. Modern MOMENTUM hardware therefore advertises with a CID assigned post-acquisition; we additionally accept the legacy Sennheiser Communications CID so we don't lose coverage on older units.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID (current) | `0x0BA3` (decimal 2979) — currently listed as **Sonova Consumer Hearing GmbH** in the SIG company-ID list |
| Manufacturer-data CID (legacy) | `0x0082` (decimal 130) — historically **Sennheiser Communications A/S**, now renamed **DSEA A/S** in the SIG list |
| 16-bit service UUID | `FDCE` — SIG-allocated to Sennheiser |
| Local name | `MOMENTUM 4`, `MOMENTUM True Wireless 4`, `MOMENTUM Sport`, `MOMENTUM Wireless`, … |
| Sample mfr-data | `a3 0b 00 c3 80` (5 bytes total: CID `a3 0b` + 3-byte payload `00 c3 80`) |

The 3-byte manufacturer-data payload is not publicly documented; we surface it as `payload_hex` for future analysis but do not interpret individual bytes.

### Match Heuristic

A sighting is classified as Sennheiser if **any** of the following hold (fallback chain):

1. manufacturer-data CID is `0x0BA3`, `0x0082`, or `0x0494`, OR
2. the 16-bit service UUID `FDCE` is advertised, OR
3. the local name starts with `MOMENTUM ` (case-insensitive).

Multiple sightings of the same MOMENTUM 4 device alternate between advertising the full ad (CID + service UUID + local name) and a stripped variant carrying only the FDCE service UUID and local name, so the fallback chain is needed to keep the device classified consistently across address rotations.

## Pro-Wireless CID 0x0494 (parser v1.1, 2026-09-29 sweep)

`0x0494` is SIG-registered to **SENNHEISER electronic GmbH & Co. KG** — the professional-audio entity (XS Wireless / evolution-wireless class gear), a different registrant than the consumer line's `0x0BA3`. Captured from 3 devices / 130 sightings across **2026-07-29 and 2026-09-26/27** (two months apart — a recurring family, not a one-off). Three frame shapes:

| Shape | Manufacturer data | Sightings |
|---|---|---|
| full | `94 04` + `02 03 a9 5a 42 xx xx xx xx 01 14 02 35 0a <batt> ff 0f 60 01 06 01 01 06 01` (26 B) | 107 |
| truncated | same prefix, ends after `ff 0f 60` (20 B total) | 4 |
| short | `94 04 01` (3 B total) | 19 |

Payload bytes 0-4 (`02 03 a9 5a 42`) are a model/firmware constant in all captures; bytes 5-8 (`xx xx xx xx`) look like a unit identifier (unverified, surfaced raw via `payload_hex`). Byte **14** is the only varying byte across the capture series: `0x4d → 0x38 → 0x37` in time order (2026-09-26 20:11 → 2026-09-27 01:38 → 01:47) = **77 → 56 → 55**, monotonically decreasing ~4%/hour with no RSSI correlation (RSSI spans -88..-101 dBm while the byte holds constant). That is battery-percent-shaped; the parser surfaces it as `battery_percent` with the inference documented. The `06 01 01 06 01` tail is opaque.

Frames on `0x0494` set `frame_type` = `pro_wireless` (full/truncated) or `pro_wireless_short` (the 1-byte `01` shape). Any other `0x0494` payload is still claimed on CID attribution alone, with no invented fields.

### Device-Class Heuristic

If the local name matches the MOMENTUM family we surface `device_class = headphones` and a stable key of `sennheiser:<model>`. Without a usable local name we fall back to `device_class = audio` and no stable key (the rotated random MAC isn't a reliable identity).

## Examples

| Capture | Inference |
|---|---|
| local name `"MOMENTUM 4"` + CID `0x0BA3` + UUID `FDCE` | model = `MOMENTUM 4`, class = `headphones`, stable key `sennheiser:MOMENTUM 4` |
| local name `"MOMENTUM 4"` + UUID `FDCE` (no mfr data) | model = `MOMENTUM 4`, class = `headphones` |
| CID `0x0BA3` alone, no name | matched on CID; model unknown; class = `audio` |
| local name `"MOMENTUM True Wireless 4"` | model = `MOMENTUM True Wireless 4`, class = `headphones` |
| CID `0x0494` full pro frame, battery byte `0x37` | `frame_type = pro_wireless`, `battery_percent = 55`, class = `audio` |
| CID `0x0494` short frame `94 04 01` | `frame_type = pro_wireless_short`, class = `audio` |

## References

- [Sennheiser MOMENTUM 4 Wireless product page](https://www.sennheiser-hearing.com/en-US/p/momentum-4-wireless/)
- [Sennheiser corporate site](https://www.sennheiser.com/)
- [Sonova completes acquisition of Sennheiser's consumer business (2021)](https://www.sonova.com/en/story/corporate/sonova-completes-acquisition-sennheisers-consumer-business)
- [Bluetooth SIG company identifiers (0x0BA3, 0x0082)](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
- [Bluetooth SIG 16-bit UUID assigned numbers (FDCE)](https://www.bluetooth.com/specifications/assigned-numbers/)
