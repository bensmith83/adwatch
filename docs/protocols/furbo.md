# Tomofun Furbo — Pet Camera (Furbo3 line)

## Overview

Furbo pet cameras (Tomofun) broadcast a BLE advertisement identified by
local name, with a manufacturer-data field that is **double-hex-encoded**
— every byte of the field is itself an ASCII hex digit, so the "raw"
manufacturer data must be decoded as ASCII first, then that resulting
string decoded as hex a second time to reach the real inner payload.

## Fingerprint

### Local Name

| Pattern | Notes |
|---------|-------|
| `Furbo*` | e.g. `Furbo3-S3` — real Tomofun product line |

### Manufacturer Data — double-hex-encoded, no real company-ID field

The app decodes company ID `0x3030` from the first two bytes, but — same
artifact shape as Night Owl WNVR — this is just the ASCII digits `"0"` +
`"0"` (0x30 0x30) read as a little-endian CID, not a real vendor signal.
The entire manufacturer-data blob decodes as printable ASCII hex digits;
decoding that ASCII string as hex a second time yields the real 6-byte
inner payload:

```
manufacturerData (ASCII):  "002db309fef0"
                             │
                             ▼ (hex-decode the ASCII string)
inner payload (6 bytes):   00 2d b3 09 fe f0
                            └──┬───┘ └──┬──┘
                          stable prefix  varying tail
                        (00 2d b3, both  (unit-specific?
                         devices)         unconfirmed)
```

Observed across 2 independent physical devices (confirmed via
`deviceIdentifier`, captures 2 days apart): the 3-byte prefix `00 2d b3`
is identical on both; the 3-byte tail differs (`09fef0` vs `075b74`) with
no confirmed relationship between the two values.

## Identification

- **Primary**: local name starts with `Furbo`, and the entire
  manufacturer-data blob decodes as printable-ASCII hex digits (which
  itself decodes cleanly as hex). This double-check keeps the parser from
  matching noise that happens to start with "Furbo" but carries a
  differently-shaped payload.
- **Device class**: `pet_camera`.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Tomofun` |
| Product | hard-coded | `Furbo` |
| `inner_payload_hex` | double-hex-decoded manufacturer data | 6 bytes; tail semantics unconfirmed |

## What We Cannot Parse

- Tail-byte semantics (n=2 samples, no confirmed relationship).
- Live device state (treat dispensing, motion/bark alerts, live-view
  session).

## Stable Identity

No confirmed per-unit identifier beyond the tail bytes (unconfirmed
stability). Anchored on `stable_key = furbo:<mac>`.

## References

- Tomofun "Furbo3" user guide (product-line confirmation).
