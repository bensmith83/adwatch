# Star Micronics TSP-series thermal receipt printer (CID 0x01B0)

## Overview

**Star Micronics Co., Ltd.** makes point-of-sale / receipt printers; the
**TSP-series** is its thermal receipt-printer line. In the 2026-10-24
sweep, four records / 29 sightings — all in one ~80-minute evening window
(2026-10-17 21:43–23:02Z, RSSI −83…−99 dBm) — advertised a 20-byte
manufacturer frame on Star's SIG **company ID `0x01B0`**, with a random
on-air address, no local name and no service data. The frame self-identifies
twice: the IEEE OUI `00:11:62` embedded at bytes 2–4 is registered to
"STAR MICRONICS CO.,LTD.", and bytes 9–17 carry the literal ASCII model
label `"TSP100IV;"`.

## Supported Models

| Model | Evidence | Notes |
|---|---|---|
| TSP100IV | ASCII label `TSP100IV;` in the payload | the only label observed (constant across all four units) |
| other TSP-series | *(none observed)* | the frame parses the model up to the `;`, so a TSP650 / TSP800 label would ride the same shape if it ever appears |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Company ID | `0x01B0` | Star Micronics Co., Ltd. (SIG-registered) |
| Manufacturer data | 20 bytes (incl. CID) | see layout below |
| Embedded OUI | `00 11 62` at bytes 2–4 | Star Micronics (IEEE MA-L) |
| Model label | `TSP100IV;` at bytes 9–17 | ASCII, constant across all four units |
| Local name | *(absent)* | |
| Service UUIDs | *(absent)* | |
| Address type | `random` | rotates; the payload echoes the unit's real BD_ADDR |

The parser gates on CID `0x01B0` **and** the Star OUI `00 11 62` **and** a
20-byte frame. The OUI gate is load-bearing: CID `0x01B0` alone is Star's
slot and could in principle be emitted by other Star products with different
frame shapes.

### Manufacturer-data layout (20 bytes, includes the 2-byte CID)

```
off  0..2   2..5      5..8       8    9..18         18..20
     b0 01 | 00 11 62 | 57 e5 3f | 20 | "TSP100IV;" | 02 20
     CID    OUI        NIC        sp    model        trailer
```

| Bytes | Value | Meaning |
|---|---|---|
| 0–1 | `b0 01` | CID `0x01B0` (Star Micronics) LE |
| 2–4 | `00 11 62` | IEEE MA-L OUI "STAR MICRONICS CO.,LTD." |
| 5–7 | `57 e5 3f` / `57 d9 23` / `57 e3 53` / `57 d9 09` | per-device NIC tail — the four units; all share the `57` prefix (a coherent `00:11:62:57:xx:xx` fleet) |
| 8 | `20` | ASCII space (constant) |
| 9–17 | `54 53 50 31 30 30 49 56 3b` | ASCII `"TSP100IV;"` — model label, parsed up to the `;` |
| 18–19 | `02 20` | constant trailer — purpose unknown (terminator-shaped), surfaced raw |

Corpus frames (full mfg, including CID):

```
b00100116257e53f2054535031303049563b0220   (18 sightings)
b00100116257d9232054535031303049563b0220   (9 sightings)
b00100116257e3532054535031303049563b0220   (1 sighting)
b00100116257d9092054535031303049563b0220   (1 sighting)
```

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Star Micronics` |
| `company_id` | hard-coded | `0x01B0` |
| `oui_owner` | hard-coded | `Star Micronics Co., Ltd.` |
| `mac` | payload bytes 2–7 | reconstructed `00:11:62:<NIC>` — the unit's own public BD_ADDR |
| `model` | payload bytes 9–17 | ASCII label up to the `;` (`TSP100IV`) |
| `trailer_hex` | payload bytes 18–19 | `0220` — opaque, no semantic claim |

### What we cannot surface

- Any per-frame telemetry — the only varying bytes are the NIC tail (per
  unit, not per sighting) and everything else is constant. There is no
  counter, status or battery field to decode.
- The meaning of the `02 20` trailer — it is left opaque, not decoded.

## Stable identity

The device echoes its own public BD_ADDR in the payload while rotating a
random/RPA on-air address (the iTECH-Fusion pattern). The reconstructed
`00:11:62:<NIC>` at bytes 2–8 is the per-unit stable key; the parser never
keys on the on-air MAC:

```
stable_key = star_tsp_printer:00:11:62:57:E5:3F   (payload-derived; survives rotation)
identifier = SHA256(stable_key)[:16]
```

## Parser scope

Passive observation only. No GATT connection, pairing or printing control is
performed or implied; the printer is identified and its model/MAC surfaced
from the advertisement alone.

## Confidence

- **Attribution: HIGH** — three independent anchors agree: the SIG company
  ID `0x01B0`, the IEEE OUI `00:11:62`, and the self-identifying ASCII model
  string `"TSP100IV;"`. This is the strongest possible attribution short of
  a GATT connection.
- **Product family: HIGH** — the model string names the TSP100IV directly;
  the frame parses other TSP-series labels by shape.
- **Frame semantics: none beyond MAC + model** — the `02 20` trailer is left
  opaque; no counter/status/battery field is claimed.

## References

- [Bluetooth SIG company_identifiers.yaml](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — CID `0x01B0` = Star Micronics Co., Ltd.
- [Star Micronics](https://starmicronics.com/) — TSP-series thermal receipt printers
- NearSight app research write-up `research/sweep-2026-10-24-candidates.md`
