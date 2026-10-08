# Ubiquiti Device Beacon (service data 0x252A factory MAC, non-UniFi-AP product lines)

## Overview

Ubiquiti's UniFi access points advertise a small BLE frame whose service
data under the 16-bit UUID `0x252A` is the unit's wired factory MAC, next
to the AP adoption UUID `3e6e0806-6562-4a01-b6cd-e3409c5f9627` (see
`ubiquiti-unifi.md`). The 2026-08-28 telemetry sweep showed the **same
0x252A-carries-the-MAC convention on other Ubiquiti product lines**, each
next to a different 128-bit UUID and with none of the AP frame's extras
(no `0x2119` uptime, no `0x2021` adoption flag, no model name):

| 128-bit service UUID | Units | Blocks (IEEE MA-L → Ubiquiti Inc) | Source |
|----------------------|-------|-----------------------------------|--------|
| `7669789E-738F-44DA-8C46-3513553720A5` | 8 (+1 with the all-FF placeholder) | `24:5A:4C` ×6, `70:A7:41` ×1 | 2026-08-26/27 scene |
| `883FF5A6-F60A-4B56-A0A3-9E22BF1B91F2` | 1 | `70:A7:41` | 2026-08-26 |
| `B4BD9342-C02F-411A-9BE5-8B6537D44A1F` | 1 | `F4:E2:C6` | July 2026 export17 pool |

Three independent Ubiquiti MA-L blocks resolving to one vendor across
three UUIDs is the corroboration a single prefix would lack, so the vendor
is certain. Which product line each UUID belongs to is **not** known — the
frames carry nothing that names one — and the parser does not guess.

A fourth data point turned up while checking OUIs: the owner-labelled sensor
(`fa-flem-sensor.md`) documented from the 2026-07-06 sweep (custom UUID
`35CD221C-02B4-4D1F-9B54-6089C861AD62`, 0x252A MAC on `58:D6:1F`) sits on a
Ubiquiti block too — that block was never looked up. Its local name
`<owner-chosen label>` is therefore most plausibly an installer-chosen
device name on a Ubiquiti product, not a vehicle-maker part. Re-attributing that
parser is filed as follow-up; this parser hands its UUID off untouched.

## Supported Models

| Model | Attribution | Notes |
|-------|-------------|-------|
| unknown Ubiquiti product lines (three UUIDs) | vendor certain, product unknown | eight units on one UUID in one commercial-building scene; four of their MACs are consecutive-batch neighbours |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data | under `0x252A`, exactly 6 bytes | the factory MAC, or `ff ff ff ff ff ff` |
| Service UUID (128-bit list) | exactly one of the UUIDs above | recorded, not routed |
| Company ID | none | |
| Local name | none | |
| Address | random | rotates; the embedded MAC does not |

One unit advertised the all-FF placeholder for an hour (102 sightings,
23:53–00:51 UTC) next to `7669789E-…` — a unit with no MAC programmed into
its BLE frame (factory-fresh or recovery state is the natural reading). It
is claimed on the UUID alone, with no stable identity.

### Frame layout (service data 0x252A, 6 bytes)

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–2 | OUI | 3 | must resolve to Ubiquiti in NearSight's curated table (`00:27:22`, `24:5A:4C`, `24:A4:3C`, `70:A7:41`, `F4:E2:C6`) — or the frame is the all-FF placeholder |
| 3–5 | NIC | 3 | per unit |

### Examples (OUIs real, NIC bytes withheld)

```
252A: 24 5a 4c xx xx xx     UUID 7669789E-…   (six units, 23:55–00:39 UTC)
252A: 70 a7 41 xx xx xx     UUID 7669789E-…   (00:00 UTC)
252A: 70 a7 41 xx xx xx     UUID 883FF5A6-…   (21:16 UTC)
252A: ff ff ff ff ff ff     UUID 7669789E-…   (placeholder, one hour)
```

## Parser Scope (passive-only)

NearSight's `ubiquiti_device_beacon` is routed on the `252a` service-data
key — the part of the convention that does not vary — and claims an
advertisement when the value is 6 bytes **and** either

- its OUI resolves to Ubiquiti (`attribution = oui`; identity anchored on
  the MAC, `stableKey = ubiquiti_device_beacon:<mac>`, `device_mac` tagged
  **unique, stable**), or
- it is the all-FF placeholder and one of the three UUIDs above is
  advertised (`attribution = service_uuid_only`; identity follows the BLE
  address, no stable key, `mac_unset = true`).

Frames carrying the UniFi-AP adoption UUID are handed off to
`ubiquiti_unifi`; frames carrying that sensor's vendor UUID are handed off to
`fa_flem_sensor` pending its re-attribution. Any other OUI stays
unclaimed. It reports `vendor` (`Ubiquiti Networks`), `product_family`
(`unknown`), `service_uuid` (whichever 128-bit UUID is advertised),
`device_mac`, `oui`, `oui_vendor`, `attribution`, `attribution_note`.
Device class `unknown` — vendor known, function not.

## Privacy

Same pattern as the UniFi AP and the Afero / CMT devices: the BLE address
rotates, the factory MAC is broadcast in the clear, so every unit is
re-identifiable across sessions and a passive scan enumerates a site's
Ubiquiti deployment — nine units, counted from the parking lot, in the
capture that produced this doc.

## What We Cannot Parse

- Which product each UUID is. Candidates with a BLE radio and no AP-style
  extras include the Protect cameras and sensors, Access readers, Connect
  displays and the cloud-gateway line; a name, a model block or a second
  scene with known hardware would settle it.
- Why one unit advertises the all-FF placeholder.

## References

- NearSight `research/sweep-2026-08-28-candidates.md` — the nine-unit
  capture, OUI resolution and the owner-labelled-sensor finding
- NearSight `research/export17-candidates.md` — the July `B4BD9342-…` unit
- `docs/protocols/ubiquiti-unifi.md` — the access-point frame this
  convention was first seen on
- IEEE MA-L registry (standards-oui.ieee.org) — `24-5A-4C`, `24-A4-3C`,
  `70-A7-41`, `F4-E2-C6`, `58-D6-1F` → Ubiquiti Inc (via
  `src/adwatch/_oui_vendors.py`)
