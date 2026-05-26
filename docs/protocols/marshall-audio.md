# Marshall Audio (Zound Industries)

## Overview

Marshall Bluetooth speakers and headphones broadcast BLE
advertisements while powered. They expose the CSR / Qualcomm audio
service UUID `0xFE8F` and a recognizable Marshall product name in
the local-name field. Live state (volume, EQ, battery, playback,
multi-speaker group) lives behind the GATT control surface and
requires a paired connection.

Marshall hardware is built by Zound Industries. The brand-correct
Bluetooth SIG company ID is **`0x065A` (Marshall Group AB)**, but
units in the field overwhelmingly broadcast non-Marshall CIDs in
the manufacturer-data prefix — `FE8F` + product name is the
practical anchor.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFE8F` | CSR (Cambridge Silicon Radio) — shared by every CSR/Qualcomm audio chip (Bose, JBL, Sony, etc.). NOT Marshall-specific on its own. |
| Company ID | `0x065A` | Marshall Group AB (SIG-assigned). Real Marshall CID; rarely seen in actual ads from production units. |
| Local name | Marshall product name | Required when matching via `FE8F` to avoid false-positive CSR-speaker matches |

### Common false-positive guard

The current parser **requires** either:
1. A localName starting with a known Marshall product line **AND** `FE8F` in the advertised service UUIDs; OR
2. Manufacturer CID equal to `0x065A`.

Plain `FE8F` alone is insufficient — every CSR-based audio device
in the room would match.

### Common CIDs seen in real Marshall captures (none of which are Marshall)

| CID | SIG-registered to | Why we see it |
|-----|-------------------|---------------|
| `0x0412` | SEFAM (French medical) | Unknown — possibly non-CID framing the scanner is misreading as a LE company-id |
| `0x0912` | Nerbio Medical Software Platforms | Historical / firmware quirk |
| `0x065A` | **Marshall Group AB** | The correct one — rarely the one actually broadcast |

Do not gate on these CIDs in either direction. Use the product-name +
`FE8F` rule.

## Wire Format (post-CID payload)

The CID prefix is followed by CSR/Qualcomm chipset bytes (audio
codec advertisement, BAP/CAP data on newer firmwares). We don't
decode them — they aren't Marshall-specific.

## Known Models

| Local Name | Product | Form Factor |
|-----------|---------|-------------|
| `STANMORE II/III` | Stanmore | Home speaker |
| `ACTON II/III` | Acton | Compact home speaker |
| `WOBURN II/III` | Woburn | Large home speaker |
| `EMBERTON / EMBERTON II` | Emberton | Portable speaker |
| `KILBURN II` | Kilburn | Portable speaker |
| `MIDDLETON` | Middleton | Portable speaker |
| `TUFTON` | Tufton | Portable speaker |
| `MOTIF` | Motif (A.N.C.) | TWS earbuds |
| `MINOR` | Minor (III) | Wireless earbuds |
| `MAJOR` | Major IV/V | Headphones |
| `MONITOR` | Monitor II A.N.C. | Headphones |
| `MODE` | Mode/Mode II | Wireless earbuds |

The parser's product-line allowlist is the prefix only (`STANMORE`,
`ACTON`, …) — edition suffixes like `II`/`III` are preserved in
`metadata["model"]`.

## Identity Hashing

```
identifier_hash = SHA256("{mac}:{local_name}")[:16]
```

Marshall units use a static BLE MAC, so MAC + name is sufficient.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | name allowlist + FE8F (or CID 0x065A) | "Marshall speaker nearby" |
| Product line | local_name prefix | STANMORE / ACTON / EMBERTON / … |
| Model | local_name | Full name incl. edition suffix |

## What Requires GATT Connection

- Battery level
- Firmware version
- EQ / preset
- Playback state, volume
- Multi-speaker grouping

## History / Bug Fix

v1 of the parser (Sources/Parsers/MarshallParser.swift) gated on CID
`0x0912` **AND** service-data key `fe8f`. That was a double bug:

- `0x0912` is registered to Nerbio Medical Software, not Qualcomm
  or Marshall (per the canonical SIG yaml).
- Real Marshall captures expose `FE8F` as a **service UUID**, not
  as a service-data entry — so the `serviceData["fe8f"] != nil`
  check rejected every real ad.

The fix (v2): name allowlist + FE8F UUID match OR Marshall CID
match. 713 sightings of a single STANMORE II that v1 missed are
now parsed.

## References

- Bluetooth SIG company identifiers yaml — confirms `0x065A` =
  Marshall Group AB, `0x0912` = Nerbio Medical, `0x0412` = SEFAM
- Bluetooth SIG member UUIDs yaml — confirms `0xFE8F` = CSR
- Marshall website (`marshallheadphones.com`) — product lineup
