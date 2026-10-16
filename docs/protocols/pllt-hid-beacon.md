# "PLLT" ASCII-serial HID beacon (pseudo-CID 0x4C50)

## Overview

A widely deployed, unattributed family of HID-class BLE peripherals whose
entire manufacturer payload is a printable ASCII serial string —
the leading "PL" of which occupies the company-ID field itself (wire
`50 4c` → pseudo-CID `0x4C50`, **not** SIG-assigned; an ASCII squat in
the same class as the Jieli "ZHJIELI" and Bluetrum frames).

17 distinct units (17 records, each with its own serial) were captured
between 2026-07-29 and 2026-10-09 by **two uploading installs**,
totalling ~1,346 sightings. Every record is nameless and
co-advertises the SIG HID-over-GATT service `0x1812`. Serials are
constant per unit across days and distinct per unit, so the serial is the
identity.

The cluster was first analysed on the 2026-08-01 NearSight sweep (5 units
then; bead adwatch-app-af7z) with "find any vendor signal" as the open
next step. That step is still open: product/FCC searches on the `LT-PA`,
`PA-00-1810`, and `PLLTPA012x` tokens return nothing. The shape — a
HID-class peripheral broadcasting its serial as ASCII —
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
"PLLTPA" + 12 digits
50 4c 4c 54 50 41 30 31 32 34 30 35 31 30 31 39 30 32
→ "PLLTPA012405101902"   (the whole string is the serial)
```

Observed compact strings begin `PLLTPA0122…` or `PLLTPA0124…`.

### Format B — dashed, 23 bytes on the wire (2/17 records)

```
"PL-LT-PA-" + 2 digits + "-" + 4 digits + "-" + 6 digits
→ "PL-LT-PA-00-1810-000357"   (the whole string is the serial)
```

Observed: final groups `000351`, `000357`, both after `00-1810`. The
three digit groups are reported raw, without meanings.

### Reading the digits (unconfirmed)

No split of the digits into model, hardware revision and serial is
confirmed, so none is decoded. One reading (2026-08-28 sweep) is `01` +
a YYMM date code + a 6-digit unit number: compact strings beginning
`012204…` / `012405…` would be 2022-04 / 2024-05 batches, the dashed
`1810` group a 2018-10 one, and two units share the same 6-digit unit
number under 2204 and 2405. It is a plausible reading, not evidence.

## Parser scope (passive-only)

NearSight's `pllt_hid_beacon` parser (2026-10-10 sweep) routes on CID
`0x4C50` and AND-requires one of the two exact grammars above (all-digit
groups, exact lengths). It reports the whole string as `serial`,
`serial_format` (`compact` / `dashed`), and on dashed strings the raw
groups `digit_group_1` / `_2` / `_3`; no model is decoded. Identity
keys off the serial string (`pllt_hid_beacon:<ascii>`), never the
rotating address.
Svc `0x1812` is reported as `hid_service_advertised` but not required.
`amazon_hid_remote` also routes on `0x1812` and correctly declines these
ads in-parser (its gate is CID `0x0171`) — no collision.

## Confidence

HIGH on the family grammar (17/17 records match one of two exact
shapes across five capture days and two uploading installs). NONE on vendor
attribution — catalogued as `vendor: Unknown` with the pseudo-CID
explicitly marked `vanity_forged`.
