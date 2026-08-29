# DAF5 bare-MAC family (vendor unattributed)

## Overview

A family of devices that broadcast an 8-byte manufacturer-data field
which is nothing but the unit's **6-byte factory MAC plus a 2-byte zero
tail**, while advertising a custom service UUID whose 32-bit prefix
starts with the stem `daf5` (e.g. `daf58a01-…`, `daf55501-…`). Because
the BLE stack LE-decodes the first two manufacturer-data bytes as a
"company ID", every unit appears under a different bogus CID — really
just the first two bytes of its own MAC.

The app consolidates what were once six separately-named parsers into
one `daf5_bare_mac_family` parser (see its header for the full
rationale). The `daf59201` stem is explicitly excluded — that one is
Anker soundcore's.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | 32-bit prefix `daf5XXXX` — **or its byte-reversed 8-hex rendering `XXXXf5da`** | any stem except `daf59201` (soundcore), in either order |
| Manufacturer data, layout `bare_mac` | `<6-byte MAC> 00 00` | exactly 8 bytes, non-zero MAC |
| Manufacturer data, layout `header_0610_mac` | `06 10 00 00 <6-byte MAC>` | exactly 10 bytes; UUID-gated only; not a TCL OUI, no `FFC0` |

Without a DAF5 UUID present, a stricter grammar applies (factory-MAC
bit checks + IEEE-registered OUI) and only the 8-byte layout is
considered — see `BareFactoryMACFrameParser`'s relationship in the app
source.

### Byte-reversed UUID rendering (2026-08-29 sweep)

Five units advertised `011EF5DA`, `0119F5DA`, `0126F5DA`, `0146F5DA` —
the wire bytes of `DAF51E01` / `DAF51901` / `DAF52601` / `DAF54601` in
the opposite order — next to the family's frame; a sixth unit the same
night advertised `DAF58301` in the documented order. CoreBluetooth
decodes a 32-bit UUID list little-endian per the Core Specification and
reports it as a bare 8-hex token, so a firmware that writes its 32-bit
UUID big-endian on the wire shows up reversed; the app never touches
the order. The stem template (`daf5XX01`) is exact in every case, so the
parser accepts an exactly-8-hex token ending `f5da`, normalises it back
to the `daf5XX01` stem it reports as `service_uuid_prefix`, and records
`service_uuid_wire_order = reversed` (`direct` otherwise) plus the token
as advertised. A 128-bit token is never treated as reversed, and the
`0000xxxx` SIG-truncated form is excluded. Each rendering is its own
registry routing key.

### The `06 10 00 00` header layout (2026-08-29 sweep)

Three units — two on Chipsguide's OUI `F4:2B:7D`, one on the IEEE-RA
sub-block `24:15:10` — put their MAC *after* a 4-byte header rather than
before a 2-byte zero tail:

```
06 10 00 00 | f4 2b 7d 11 22 33      + 011EF5DA   (90 sightings in two minutes)
06 10 00 00 | f4 2b 7d 44 55 66      + 0146F5DA
06 10 00 00 | 24 15 10 aa bb cc      + 0126F5DA
```

(OUIs real, NIC bytes synthetic — the embedded MAC is a device
identifier.)

The header is byte-for-byte the vanity company ID `0x1006` layout that
TCL King appliances use (`tcl-appliance.md`: `06 10 00 00` + a TCL OUI,
beside `FFC0`), which suggests one BLE-module SDK behind both — but the
DAF5 stems, the non-TCL OUIs and the absence of `FFC0` separate the two
populations cleanly. The family claims this layout only when a DAF5 UUID
is present; a TCL OUI or an `FFC0` advertiser is left to the TCL parser,
and `0x1006` is deliberately not one of the family's routing keys.

## Observed stems

| Stem | First seen | Embedded-MAC OUI | Notes |
|------|-----------|------------------|-------|
| daf51901 | 2026-08-28 | `2c:fd:b3` (Tonly Technology) | advertised reversed (`0119F5DA`); `bare_mac` layout |
| daf51e01 | 2026-08-26 | `f4:2b:7d` (Chipsguide Technology) | advertised reversed (`011EF5DA`); `header_0610_mac` layout; 90 sightings / 2 min |
| daf52601 | 2026-08-28 | `24:15:10` (IEEE RA sub-block, unresolved) | advertised reversed (`0126F5DA`); `header_0610_mac` layout |
| daf54101 | pre-2026-08 | — | consolidated from `unknown_6ccf_daf54101` |
| daf54601 | 2026-08-28 | `f4:2b:7d` (Chipsguide Technology) | advertised reversed (`0146F5DA`); `header_0610_mac` layout |
| daf54801 | 2026-08-11 | `f4:9d:8a` (Fantasia Trading LLC — Anker) | **663 sightings in one 3-minute window** (2026-08-13 sweep; registration key added) |
| daf54901 | pre-2026-08 | `88:0e:85` (Shenzhen Boomtech) | consolidated from `cid_0e88_cluster` |
| daf55501 | pre-2026-08 | `a4:c1:39` | consolidated from `unknown_c1a4_daf55501` |
| daf56001 | 2026-08-07 | `a4:c1:39` | 135 sightings / 6 min (2026-08-13 sweep; registration key added) |
| daf56201 | pre-2026-08 | — | consolidated from `unknown_9d84_daf56201` |
| daf58301 | 2026-08-28 | `98:47:44` (Shenzhen Boomtech) | documented order; `bare_mac` layout |
| daf58a01 | pre-2026-08 | — | consolidated from `unknown_6c14_daf58a01` |
| daf58e01 | pre-2026-08 | — | see `unknown-fe7c-daf58e01.md` |

The stem list can only grow from real captures. The parser's gate
accepts **any** non-excluded `daf5` stem in either byte order; the
registry needs a routing key per stem *and per rendering* for the ad to
reach it — the 2026-08-13 sweep found two stems whose records satisfied
the gate but were never routed (798 sightings between them), and the
2026-08-29 sweep found five more the same way (100 sightings).

## Privacy note

The unit rotates its BLE address but broadcasts its permanent factory
MAC in the clear, so the rotation provides no privacy. Identity keys on
the embedded MAC, on both layouts.

## Confidence / Attribution

No vendor is claimed. The OUIs the family lands in are all commodity
audio / BLE-module ODMs or the brands that buy from them: Dongguan
Huayin (`a4:c1:39`, two stems), Shenzhen Boomtech (`88:0e:85`,
`98:47:44`), Tonly Technology (`2c:fd:b3`), Chipsguide Technology
(`f4:2b:7d`), and — a correction to earlier revisions of this page,
which recorded it as having no MA-L entry — `f4:9d:8a` is IEEE-registered
to **Fantasia Trading LLC, Anker's US entity**, the same block behind
soundcore's own `daf59201` captures. Together with the `06 10 00 00`
header shared with TCL King's appliance beacon, the picture is one
Bluetooth-audio SoC/module SDK convention (a stem per product line, the
factory MAC in the clear) used across several ODMs and brands, rather
than a single device vendor. Nothing in the captures names the SDK.
