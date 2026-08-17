# "CP" Coin-Cell Beacon Fleet — vanity CID `0x320E`

## Overview

A fleet of nameless BLE beacons that identify themselves only by a forged
company ID and a two-character ASCII magic. **No vendor is claimed.** The
device broadcasts nothing that could attribute it — no MAC, no local name,
no service UUID — and no public source documents the signature. What this
document records is a byte map, a battery field, and an honest statement of
what the fingerprint does *not* tell us.

First observed 2026-08-04: 82 advertisements from **76 distinct units**
inside a single nine-minute window, in a dense mixed residential/commercial
capture in the USA.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x320E` | **Not SIG-assigned** — ~8,700 IDs above the highest real assignment (~`0x10FE`). A vanity/forged value. |
| Magic | ASCII `CP` at offset 2, then `09 40` | 82/82 records |
| Frame length | exactly 26 bytes (CID + 24) | 82/82 |
| Local name | absent | 82/82 |
| Service UUIDs | absent | 82/82 |
| Address type | random | 82/82 |
| Device class | `unknown` | no product class claimed |

## BLE Advertisement Format

### Identification

Gate on **both** signals — the CID alone is a forged 16-bit value and would
be unsafe on its own:

1. Manufacturer data company ID `0x320E` (on-wire bytes `0e 32`), **AND**
2. the 4-byte constant `43 50 09 40` (`"CP"` + `09 40`) at wire offset 2.

### Byte map

```
 0  1 | 2  3  | 4  5  | 6  | 7  | 8  9 10 11 | 12 13 | 14 | 15 ... 25
0e 32 | 43 50 | 09 40 | ff | 00 | bb bb bb bb| vv vv | cc | tail
CID     "CP"    const  flags 00     body       batt mV ctr
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0x320E` (LE `0e 32`) | 82/82 |
| 2–3 | ASCII `CP` | 82/82 |
| 4–5 | constant `09 40` | 82/82 |
| 6 | flags — `0x01` (61 records), `0x11` (19), `0x00` (2) | bit 4 distinguishes `0x01`/`0x11`; meaning unknown |
| 7 | `0x00` | 82/82 |
| 8–11 | zero on flags `0x01`/`0x11`; high-entropy on flags `0x00` | 80/82 zero |
| 12–13 | **battery millivolts**, little-endian uint16 | 2984–3058 mV across all 82 |
| 14 | counter or nonce — **not decoded** | 40 distinct values, non-monotonic against battery |
| 15–25 | zero on flags `0x01`/`0x11`; high-entropy on flags `0x00` | 80/82 zero |

### Two frame variants

- **Telemetry** (flags `0x01` / `0x11`, 80 records) — body and tail zeroed;
  the firmware broadcasts a fixed 26-byte buffer it does not fill.
- **Opaque** (flags `0x00`, 2 records) — bytes 8–11 and 15–25 carry
  high-entropy content, plausibly an encrypted or rotating body. The
  battery field stays at the same offset.

### How the battery field was confirmed

Range alone would be weak evidence. The claim rests on the two opaque
frames: they randomise every byte around bytes 12–13 and still land on a
plausible coin-cell voltage there — 3016 mV and 3007 mV, both with high
byte `0x0B`. Two independent random bodies agreeing on that high byte has
probability ≈ 1.5e-5. A misidentified field does not survive that test.

The fleet-wide range (2984–3058 mV, mean 3011) is also exactly where a
population of CR2032 cells in service sits.

## Parser Scope (Passive Only)

The parser reports frame kind, flags byte, battery millivolts, the counter
byte as an opaque value, and the raw payload. It claims no vendor and no
device class.

**Identity:** the frame contains no per-unit stable value — battery and
counter both change between sightings — so identity can only anchor on the
(rotating) BLE address. The parser records that limitation rather than
manufacturing stability the wire format does not provide. Unit counts from
this family are therefore an *upper* bound over long windows.

## What We Cannot Parse

- Vendor, brand, OEM, product class
- The meaning of the flags bits, including what distinguishes `0x01` from `0x11`
- Byte 14 (counter vs. nonce vs. second sensor channel — tested and
  non-monotonic against battery, so not a second analog reading)
- The contents of the flags-`0x00` opaque body
- Any per-unit serial — there isn't one in the frame

## Confidence / Attribution

**HIGH on structure. NO vendor attribution, deliberately.**

`0x320E` is absent from the Bluetooth SIG `company_identifiers.yaml` and
independently absent from Nordic's `bluetooth-numbers-database` mirror, so
it carries zero registry evidence. A dedicated OSINT pass found **no hits
at all** for the byte signature (`0e3243`, `43500940`, `0e324350`), for
`0x320E`, or for `12814` across general web search, GitHub-restricted
search, Theengs Decoder / OpenMQTTGateway, ESPHome, Home Assistant, and
reelyActive's observed-identifier reference.

### The big-endian near-miss — tested and REFUTED

Read big-endian, wire bytes `0e 32` give `0x0E32` = **PACIFIC INDUSTRIAL
CO., LTD.**, a genuine SIG member. This is a real failure mode: firmware
that emits the company ID big-endian is a known bug, and two confirmed
instances exist elsewhere in this corpus (Telink `0x0347`, Nespresso
`0x0225`). It does not hold here:

- Pacific Industrial's TPMS line is **RF, not BLE** — they publish no BLE
  product.
- Bytes 12–13 cannot be a tyre-pressure reading. Across 76 sensors a
  pressure field would vary enormously; a 2.5% spread (2984–3058) is a
  battery rail.

A name match with contradicting payload semantics is not an attribution.
Recorded here so the next analyst does not have to re-derive the rejection.

### Deployment reading

76 units in one place, cells all within 74 mV of each other (too tight for
a fleet that accumulated over years), broadcasting a mostly-zeroed 26-byte
buffer with no per-unit ID anywhere in it. That reads as a homogeneous,
recently-commissioned or as-yet unprovisioned tag fleet — the white-label
beacon-module class (Minew/Moko/KKM/Feasycom and similar) configured by a
systems integrator, which is typically unattributable from the air
interface alone.

Note this *weakens* the electronic-shelf-label hypothesis rather than
supporting it: ESL, RTLS and asset-tracking deployments all require a
stable per-device ID in the payload or the address, and no ESL vendor
documents a "CP" magic, a 26-byte advert, or a vanity CID.

RSSI spans −106..−57 dBm, consistent with many physically distinct units at
varying range rather than one device seen repeatedly.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x320E` absent, highest
  assigned ≈ `0x10FE` (fetched 2026-08-07)
- [NordicSemiconductor/bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database)
  — independent mirror, `12814` absent
- [reelyActive BLE identifier reference](https://reelyactive.github.io/ble-identifier-reference.html)
  — no entry; carries the relevant warning that a device advertising a
  company code is not necessarily that company's product
- NearSight `Sources/Parsers/UnknownCP320EBeaconParser.swift`
