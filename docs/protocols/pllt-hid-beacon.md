# "PLLT" ASCII-serial HID beacon (pseudo-CID 0x4C50)

## Overview

A widely deployed, unattributed family of HID-class BLE peripherals whose
entire manufacturer payload is a printable ASCII model+serial string —
the leading "PL" of which occupies the company-ID field itself (wire
`50 4c` → pseudo-CID `0x4C50`, **not** SIG-assigned; an ASCII squat in
the same class as the Jieli "ZHJIELI" and Bluetrum frames).

17 distinct units (distinct serials) were captured between 2026-07-29 and
2026-10-09 across **17 independent uploaders** — i.e. 17 different
households — totalling ~1,346 sightings. Every record is nameless and
co-advertises the SIG HID-over-GATT service `0x1812`. Serials are
constant per unit across days and distinct per unit, so the serial is the
identity.

The cluster was first analysed on the 2026-08-01 NearSight sweep (5 units
then; bead adwatch-app-af7z) with "find any vendor signal" as the open
next step. That step is still open: product/FCC searches on the `LT-PA`,
`PA-00-1810`, and `PLLTPA012x` tokens return nothing. The shape — a
HID-class peripheral broadcasting its model and serial as ASCII —
suggests a small-OEM remote / presenter / pad, but that is a guess, not
evidence, and no vendor is claimed.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | pseudo-CID `0x4C50` (wire `50 4c` = "PL") | unassigned; first two payload characters |
| Service UUID | `0x1812` (HID over GATT) | 17/17 records — corroboration, not a gate |
| Local name | none | 17/17 |
| Address | random | rotates; the serial does not |
| Device class | `peripheral` | |

## Ad Format — two ASCII grammars

### Format A — compact, 18 bytes on the wire (15/17 records)

```
"PLLTPA" + 4-digit model + 8-digit serial
50 4c 4c 54 50 41 30 31 32 34 30 35 31 30 31 39 30 32
→ "PLLTPA012405101902"   (model "0124", serial "05101902")
```

Observed models: `0122`, `0124`. Example units (serials partially
redacted): `PLLTPA01240510xxxx`, `PLLTPA01220410xxxx`.

### Format B — dashed, 23 bytes on the wire (2/17 records)

```
"PL-LT-PA-" + 2-digit hw rev + "-" + 4-digit model + "-" + 6-digit serial
→ "PL-LT-PA-00-1810-000357"   (hw "00", model "1810", serial "000357")
```

Observed: serials `000351`, `000357` on model `1810`, hw rev `00`.

## Parser scope (passive-only)

NearSight's `pllt_hid_beacon` parser (2026-10-10 sweep) routes on CID
`0x4C50` and AND-requires one of the two exact grammars above (all-digit
model/serial groups, exact lengths). It reports `model`, `unit_serial`,
`serial_format`, and the full `ascii_string`; identity keys off the
serial string (`pllt_hid_beacon:<ascii>`), never the rotating address.
Svc `0x1812` is reported as `hid_service_advertised` but not required.
`amazon_hid_remote` also routes on `0x1812` and correctly declines these
ads in-parser (its gate is CID `0x0171`) — no collision.

## Confidence

HIGH on the family grammar (17/17 records match one of two exact
shapes across five capture days and 17 households). NONE on vendor
attribution — catalogued as `vendor: Unknown` with the pseudo-CID
explicitly marked `vanity_forged`.
