# Revvo Tire Sensor / In-Vehicle Gateway (CID 0x086C)

## Overview

Revvo Technologies, Inc. holds Bluetooth SIG **company identifier
`0x086C`**. Revvo is a fleet smart-tire company: their in-tire sensors
(FCC ID **2BMHZ-SENSOR-SSV11**, "Revvo PRO Tire Sensor", granted
2025-03-03) are vulcanized to the tire's inner liner — one per tire —
and report pressure/temperature/tread data "to Revvo in-vehicle gateways
or vehicle telematics via BLE" (revvo.ai). A Revvo-equipped vehicle
therefore carries several 0x086C transmitters simultaneously.

Both captures to date look exactly like that: a burst of distinct
random-address devices sharing the CID inside a short window (11 units
over an afternoon on 2026-08-28; a second cluster inside 8 seconds on
2026-08-30 — a passing vehicle). No local names. The 08-28 units also
advertised service UUIDs 180A plus a Nordic-LBS-style 128-bit UUID with
altered digits (`00001524-1312-EFDE-1523-785FEABCD128`).

No public byte-format documentation exists — the FCC filing's
operational description is confidential — so everything below the CID is
**fingerprint-inferred** from 13 distinct frames across two days.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x086C` (wire `6c 08`) | SIG-assigned to Revvo Technologies, Inc. |
| Payload length | exactly 0 or 24 bytes | hard gate; other shapes left unclaimed |
| Address | random, rotating | no payload-stable identity |

### Frame shapes

**`cid_only`** — the two CID bytes and nothing else. The majority shape
on 2026-08-28 (8 of 11 units).

**`record_stream`** — 24 payload bytes = three 8-byte cells. The frame
is a **sliding window over a longer cyclic record stream**: consecutive
frames from one unit repeat the previous frame's cells shifted left by
one cell.

### Cell taxonomy (inferred)

```
Neighbor cell:   94 08 35 1b 07 XX YY RR
  [0..5)   constant 94 08 35 1b 07 across every unit and both days —
           a batch/product constant, NOT an IEEE OUI (absent from
           MA-L / MA-M / MA-S registries)
  [5..7)   per-unit id (9 distinct values so far)
  [7]      int8; every observed value decodes to −96…−62 dBm and it
           varies between sightings while [0..7) stays fixed —
           received-RSSI-shaped (inter-sensor link measurement)

Stat cells:      5-byte id + counter-shaped words
  ids seen: 42 02 de d8 4f / 42 02 d6 71 51 / f4 02 e0 3e 4e
  then:     a 00 01 2a e3-style word shared across units within one
            day (00 01 29 e3 two days earlier — day-counter-shaped),
            further 00 00 10 xx / 00 00 16-17 xx / 00 03 xx xx words,
            zero padding
```

Stat-cell words are deliberately **not decoded** — with no vendor ground
truth they could be pressure, temperature, uptime or sequence fields,
and inventing semantics is how wrong attributions happen.

## Parser Scope (Passive Only)

`RevvoParser` (`revvo`, deviceClass `sensor`) in the NearSight app:

- Gates on CID 0x086C AND payload length ∈ {0, 24} only.
- Emits `frame_type` (`cid_only` / `record_stream`), the three cells raw
  as `cells_hex`, and for neighbor cells `neighbor_ids` /
  `neighbor_rssi_dbm` / `neighbor_count`.
- Identity keys on the (rotating) MAC; no stableKey — the window rotates
  and the neighbor set is shared across a vehicle's sensors, so nothing
  in the payload is per-transmitter stable.

## Attribution Confidence

**Vendor: high.** SIG registry assignment plus FCC-corroborated product
line plus a burst pattern that matches a multi-sensor vehicle. **Field
semantics: low** — everything above the CID gate is inferred from 13
frames; the neighbor-id/RSSI split is the only decode confident enough
to surface as named metadata, and it is labeled as inferred in the
parser header. Whether a given transmitter is a tire sensor or the
in-vehicle gateway is not distinguishable passively.

## References

- Bluetooth SIG Assigned Numbers — company identifier 0x086C
- [FCC ID 2BMHZ-SENSOR-SSV11 — Revvo PRO Tire Sensor](https://fccid.io/2BMHZ-SENSOR-SSV11)
- [Revvo tire sensor options (BLE reporting to in-vehicle gateways)](https://www.revvo.ai/tire-sensor-options/)
- NearSight beads nearsight-25td (capture history), app research write-up
  `research/sweep-2026-08-31-candidates.md`
