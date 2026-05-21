# OnePlus Plugin

## Overview

**OnePlus** (Shenzhen) has been an **OPPO** sub-brand since 2021 and shares an Android peripheral / cross-device proximity stack with OPPO and Realme. The marketing name for that stack varies — **Heytap**, **OPPO Cross-device interconnection**, **OnePlus Spirit** — but the BLE advertisement format is common across the three sister brands.

We detect OnePlus phones (and OnePlus Buds accessories announcing via the phone-relay) by latching onto two SIG-allocated signals: the OnePlus Technology manufacturer-data company ID **0x072F** and the **Heytap** 16-bit service UUID **686B**. The 686B service-data payload literally embeds the marketing model name as ASCII at the end of the buffer, e.g. `"OnePlus 11 5G"` — that ASCII tail is the killer signal that lets us cleanly separate OnePlus broadcasts from OPPO / Realme broadcasts on the same UUID.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x072F` (little-endian raw `2f 07`) — OnePlus Technology (Shenzhen) Co., Ltd. |
| Service UUID (16-bit) | `686B` — Heytap / OPPO cross-device ecosystem |
| Local name | absent |
| Sample mfr-data | `2f07af302b1488004c264000000000fd2e60177507` (21 bytes: CID + 19-byte payload) |
| Sample mfr-data variant | `2f07af302b1488004c264800000000c846625f0007` (first 8 bytes shared, tail rotates) |
| Sample 686B service-data | `f5345e015cf7084f6e65506c7573203131203547` |

### Service-data layout (686B)

```
| 7-byte header / token        | ASCII model name run                     |
| f5 34 5e 01 5c f7 08         | 4f 6e 65 50 6c 75 73 20 31 31 20 35 47   |
|                              | "O  n  e  P  l  u  s     1  1     5  G"  |
```

The leading 7 bytes look like a per-device token (likely a salted MAC-derived handle that OnePlus rotates for privacy, matching the random-address rotation we see in captures). The trailing bytes are a printable-ASCII marketing name — anywhere from ~10 to ~25 bytes. Observed values include `OnePlus 11 5G`; Heytap on OPPO peers emits names like `OPPO Find X7`, `Realme GT 5 Pro`, etc. on the same UUID.

### Manufacturer-data layout (0x072F)

`2f07af302b1488004c264000000000fd2e60177507`

```
2f 07 | af 30 2b 14 88 00 4c 26 | 40 00 00 00 00 | fd 2e 60 17 75 07
CID   | 8-byte header (stable across samples)
                                | 5-byte slot (40 = device-type flag?)
                                                | 6-byte rotating tail
```

The first 8 bytes of the payload (`af302b1488004c26`) match across multiple captures and are likely a static device-fingerprint header; bytes 9-13 change between connection states (we see `40 00 …` vs `48 00 …`) and the trailing 6 bytes rotate on every advertisement. We do not currently decode any of this — the CID alone is enough to peg the broadcast to OnePlus, and the 686B service-data ASCII tail is what gives us the marketing model.

### Matching rule

We match if:
- `companyID == 0x072F`, OR
- `serviceData["686B"]` contains a trailing printable-ASCII run of length >= 7 that starts with `OnePlus` or `One Plus` (Heytap sometimes inserts a space, especially on Buds broadcasts).

We surface `device_class = phone` by default. If the captured ASCII model contains `Buds`, `Headphone`, or `Earphone`, we re-classify to `earbuds`. The stable key is `oneplus:<model>` whenever an ASCII model was captured.

## Examples

| Capture | Inference |
|---|---|
| CID `0x072F` + 686B service-data with ASCII `OnePlus 11 5G` | model = `OnePlus 11 5G`, class = `phone`, stableKey = `oneplus:OnePlus 11 5G` |
| 686B service-data ASCII `One Plus Buds 3` (no CID) | model = `One Plus Buds 3`, class = `earbuds` |
| CID `0x072F` alone, no 686B service-data | matched on CID; class = `phone`, no stable key |
| 686B service-data with no ASCII model run | not matched (could be OPPO or Realme — handled elsewhere) |

## References

- [Bluetooth SIG assigned company identifiers (0x072F = OnePlus Technology)](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
- [OPPO ColorOS cross-device interconnection](https://www.coloros.com/en/)
- [OnePlus / OPPO merger background, 2021](https://www.oneplus.com/global/community)
- [Heytap account / cross-device cloud](https://www.heytap.com/en/)
