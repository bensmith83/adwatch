# Samsara fleet telematics devices (service UUID 0xFCE5)

> Sibling family: a second Samsara member UUID, `0xFC86`, carries a
> distinct 24-byte service-data frame — see `samsara-fc86.md`
> (2026-10-05 nightly sweep).

## Overview

**Samsara Networks, Inc.** holds the Bluetooth SIG *member* 16-bit service
UUID `0xFCE5` (member UUIDs are allocated only to SIG member companies) and
the IEEE MA-L block `FC:DB:21`. Samsara sells connected-fleet hardware:
vehicle gateways (VG series), powered and unpowered asset gateways (AG
series), AI dash cams (CM series), environmental monitors (EM series) and
the **AT-series Bluetooth asset tags** (AT11 / AT11X, and the newer AT12 /
AT13 "Asset Tag XS"). Samsara's own documentation says an asset tag
"broadcasts an encrypted device ID to nearby Samsara gateways or mobile
devices running a Samsara app", which use the Bluetooth signal to place it.

Twelve units were captured passively between 2026-07-29 and 2026-08-30,
each seen once or twice at −79..−102 dBm from a random address with no
local name and no scan response — the signature of Samsara-equipped
commercial vehicles (and the tags on their trailers or equipment) passing a
house. Every one advertises `0xFCE5`; two carry it as a **service-data**
key and embed a reversed factory MAC in Samsara's own OUI block, which is
what turns a UUID lookup into an attribution. The 2026-09-19 merged corpus
added **eight more service-data records** (all one-off drive-bys,
−79..−102 dBm), re-verified below — the map holds on all of them. One new
MAC (`fc:db:21:89:ca:c3`) appears on two records with different entropy
regions — the MAC is the unit identity, the rest rotates — and three of
the eight share the `fc:db:21:89:ca:xx` block, plausibly one fleet's
sequentially-issued hardware.

| First seen (UTC) | Carrier | Frame type | Units | RSSI |
|------------------|---------|------------|-------|------|
| 2026-07-29 17:40–18:12 | manufacturer data + `0xFCE5` in the UUID list | `0x02` | 3 | −94..−102 |
| 2026-08-11 13:26–14:03 | manufacturer data + UUID list | `0x02` | 2 | −93..−97 |
| 2026-08-28 13:06–16:44 | manufacturer data + UUID list | `0x32` | 4 | −91..−98 |
| 2026-08-28 16:33 | service data `0xFCE5` | `0x02` | 1 | −95 |
| 2026-08-30 16:29 | service data `0xFCE5` | `0x02` | 1 | −79 |
| 2026-08-30 19:19 | manufacturer data + UUID list | `0x32` | 1 | −89..−98 |
| 2026-09-19 corpus | service data `0xFCE5` | `0x02` ×7, `0x42` ×1 | 8 | −79..−102 |

## Supported models

None pinned. Nothing in the frames names a model and no Samsara document
describes the advertisement. The `0x02` frames' coin-cell-range word (see
below) and high-entropy body match Samsara's description of the asset
tags' encrypted broadcast; the `0x32` frames (all-zero body) are a second
product or mode. Both are reported as the Samsara family with the product
left open.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFCE5` | SIG member UUID → *Samsara Networks, Inc*. Present on 12/12 records: as the service-data key on 2, in the advertised UUID list on 10 |
| Embedded MAC | 6 bytes at [6..12), **reversed** | Service-data frames only; `fc:db:21:ac:2b:71` and `fc:db:21:ad:fa:ce` — IEEE MA-L `FC:DB:21` = SAMSARA NETWORKS INC |
| "Company ID" bytes | `02 1f` / `32 20` / `32 00` | Read as CIDs 0x1F02 / 0x2032 / 0x0032 on the manufacturer-data frames — none SIG-assigned, high byte varies within the family. A frame header, not a company id |
| Address type | random, one sighting per unit | No unit was seen twice, so rotation cannot be measured |
| Local name | none | |
| Device class | `vehicle_telematics` | |

## Ad Format — 22 bytes, three observed shapes

```
service data 0xFCE5   02 1d | 10 0a | d0 0b | 71 2b ac 21 db fc | 00 00 00 10 81 01 e2 8e 6a db
manufacturer data     02 1f | 0d 0f | b8 0b | 48 76 5a 20 96 05 | 39 f0 d9 48 e4 02 4d 8b 2e f4
manufacturer data     32 20 | 14 0f | 6a 09 | 35 cf 98 96 03 00 | 00 00 00 00 00 00 00 00 00 00
offset                0       1..4    4..6    6..12               12..22
                      type    header  u16 LE  unit field          body
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0 | frame type | `0x02` on 7 units (both carriers), `0x32` on 5 (manufacturer data only) |
| 1–3 | header | `1d 10 0a` on both service-data units; `1f 0d XX` (XX = 0f/0c/3f/0e/0f) on the `0x02` manufacturer frames; `20/00 14 0f` on the `0x32` frames. Reported raw as `header_hex` |
| 4–5 | 16-bit little-endian word | 3000, 3000, 2801, 2801, 3000 (`0x02` mfg), 3024 ×2 (service data), 2685, 2410, 1320, 2410, 2410 (`0x32`). A coin-cell millivolt battery reading fits the range and the product line, but nothing confirms it — reported raw as `u16_le_at_4` with a note |
| 6–11 | 6-byte unit field | Different on every unit. On the service-data frames it reverses to a `fc:db:21` factory MAC; on the manufacturer frames it reverses to no registered OUI (e.g. `05:96:20:5a:76:48`) and is surfaced as `unit_field_hex` only |
| 12–21 | body | High-entropy on the `0x02` frames (consistent with the "encrypted device ID" Samsara describes), `00 00 00` + 7 bytes on the service-data frames, all zero on `0x32` |

### Parser gate

Either

- `0xFCE5` service data of exactly 22 bytes, **or**
- `0xFCE5` in the advertised service-UUID list **and** manufacturer data of
  exactly 22 bytes whose first byte is `0x02` or `0x32`.

The same 22 manufacturer-data bytes without the UUID are left unclaimed —
the UUID is the vendor evidence; the leading bytes are not. NearSight's
registry matches a service-UUID routing key against both the service-data
keys and the advertised UUID list, so one `fce5` registration reaches both
carriers.

**Shipped scope (2026-09-19):** NearSight's `SamsaraParser` v1.0 currently
claims **only the service-data carrier**, with the additional structural
gates verified against all 8 service-data records in the 2026-09-19
corpus: `[1] == 0x1d`, `[4..6) == d0 0b` (constant 3024 on all ten
service-data records seen so far — the u16-LE battery reading the
manufacturer frames vary), `[12..15) == 00 00 00`, frame type `0x02` or
`0x42`, and the reversed `[6..12)` MAC required to resolve to the
`FC:DB:21` OUI. The manufacturer-data carrier is documented here but
deliberately unclaimed: the 2026-09-19 pool contained no such records, and
gating unobserved shapes is how parsers over-claim. It is the first
extension candidate the moment one re-enters a corpus.

Refined service-data byte map (2026-09-19, 8 records):

```
[0]      frame type — 0x02 (7) or 0x42 (1)
[1]      0x1d (constant)
[2..4)   per-frame word — 0d07 / 0d08 / 0d09 / 0d0a / 1009 (reported raw)
[4..6)   d0 0b (constant 3024 on every service-data record)
[6..12)  factory MAC, REVERSED — all 8 resolve to FC:DB:21
[12..15) 00 00 00 (constant)
[15]     flags byte — low nibble always 0 (reported raw)
[16..18) per-frame word, uint16 LE — 284..1166, near-stable per unit
         (968 -> 967 on the one unit captured twice; semantics unknown)
[18..22) high entropy (the encrypted device payload; not decoded)
```

## Identity Hashing

```
service-data frame with a fc:db:21 MAC:
    identifier = SHA256("samsara_fce5:{embedded_mac}")[:16]
    stableKey  = "samsara_fce5:{embedded_mac}"   (bd_addr tagged uniqueStable)
any other frame:
    identifier = SHA256(ble_address)[:16]
    stableKey  = nil
```

The two service-data units advertise from random addresses and then
broadcast their permanent hardware MAC, so the MAC is the identity anchor
for them. The other ten carry no field known to be stable, so identity
stays on the address until a unit is seen twice.

## What We Cannot Parse

- Which product each frame type is (asset tag vs gateway vs monitor)
- Whether the word at [4..6) is a battery voltage
- The meaning of the header bytes and the body (Samsara says the tag's
  device ID is encrypted; the `0x02` body looks like it)
- Any state or telemetry

## Detection Significance

A sighting means **a Samsara-connected fleet asset is within BLE range** —
a delivery van, a truck cab, a tagged trailer or piece of equipment. The
service-data variant re-identifies its unit across sessions by the factory
MAC it broadcasts in the clear.

## Confidence / Attribution

**Vendor: high.** A SIG member service UUID registered to Samsara on every
record, corroborated on two units by a factory MAC in Samsara's IEEE MA-L
block inside the same frame.

**Product: low / not claimed.** The family is a fleet-telematics device;
the model is not pinned.

**Field semantics: low.** Header, word, unit field and body are reported
raw; only the reversed-MAC reading of the unit field on the service-data
frames is asserted, and only when the OUI resolves to Samsara.

## References

- Bluetooth SIG `member_uuids.yaml` — `0xFCE5 = Samsara Networks, Inc`.
- IEEE MA-L registry — `FC:DB:21 = SAMSARA NETWORKS INC`.
- Samsara Help Center, "Bluetooth Location Tracking for Asset Tag (AT11)"
  and "Asset Tag Models" (kb.samsara.com); Samsara product page
  "Asset Tag" (AT12 / AT13) — the encrypted-broadcast and gateway-detection
  description.
- NearSight `SamsaraParser` (`Sources/Parsers/SamsaraParser.swift`,
  shipped 2026-09-19) and `research/sweep-2026-09-19-candidates.md` — the
  sweep that shipped the parser and re-verified this doc against 8 new
  service-data records. The doc itself was derived by the 2026-09-02
  nightly sweep (`research/sweep-2026-09-02-candidates.md`); the
  2026-08-29 sweep had logged the `0x32` shape as "not a CID" without
  resolving the UUID.
