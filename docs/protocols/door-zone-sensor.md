# Door Zone Sensor (Unattributed Vendor)

## Overview

A family of BLE-only door-contact sensors that advertises **nothing but a
local name** of the form `"Door<N> "` (note the trailing space). No
manufacturer data, no service UUIDs, no service data, no scan-response —
just a 6-byte ASCII name and a rotating random address.

Captured in `research/adwatch_export 17.json` (three distinct units —
`Door1 `, `Door2 `, `Door4 ` — 990 combined sightings over a single capture
window, RSSI −102 to −75). Vendor attribution is unconfirmed; the shape is
consistent with a **multi-zone alarm panel exposing each contact as a
separate BLE peripheral**, or a **DIY ESP32 / nRF52 contact sensor** named
by zone index.

We catalogue the family as `vendor: Unknown` so the units can be
counted, grouped, and disambiguated from generic random-address
nameless noise — and so future ground-truth captures can upgrade the
attribution.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `Door<digits><space>` (1–4 contiguous digits, trailing ASCII space `0x20`) | The trailing space is significant — it's reproducible across all three observed units and excludes generic "Door"-named devices (Yale "Door Lock", "Door Sensor", etc.) |
| Address type | `random` | rotating private address |
| Manufacturer data | (absent) | — |
| Service UUIDs | (absent) | no primary advertisement service list |
| Service data | (absent) | — |

### Why the gate is strict

A naive `"^Door"` gate would over-match: Yale door locks (`"YRD256-..."`),
Schlage Encode (`"Schlage Door"`), GE/Aladdin garage openers (`"Door Opener"`),
and several smart-home hubs all carry "door" in their names. The trailing
space + `\d+` constraint cuts the search to a much tighter family.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Unknown` |
| Product family | hard-coded | `Door Zone Sensor` |
| Device class | hard-coded | `contact_sensor` |
| Zone number | localName | The `<digits>` between "Door" and the trailing space — e.g. `1`, `2`, `4` |
| Adv shape | hard-coded | `name_only_zoned` — useful diagnostic when grouping similar emitters |
| Verification hint | hard-coded | active-scan in nRF Connect; check public MAC OUI; GATT-connect for Device Information Service (0x180A) |

### What We Cannot Parse from the Advertisement

- Open / closed state (the whole point of a contact sensor).
- Tamper or low-battery flags.
- Vendor / model confirmation.

The vendor either reserves the open/closed bit for a GATT
characteristic that needs a connection, or it lives in a scan-response
that this passive capture didn't trigger. Active scanning + nRF Connect
GATT explore would settle both questions in under two minutes.

## Stable Identity

Per-unit identity anchors on the zone number, which survives MAC rotation
and is the only stable element of the advertisement:

```
stable_key = door_zone_sensor:zone:<digits>
```

This means **two unrelated installations that both happen to expose
"Door1 " collapse into one logical device** in our records. That's an
accepted limitation — until we have richer evidence (mfg data, GATT
characteristics, OUI) there's no other per-unit signal to key on. If
both units appear in the same capture window, the per-MAC variant ads
will surface them as two sightings of the same `stable_key`, which is
the correct grouping behaviour for this family.

## Detection Significance

- Suggests a multi-zone alarm panel or DIY contact-sensor cluster.
- Three units with sequential numbering (1, 2, 4 — note the gap) in a
  single capture is consistent with a residential panel where zone 3
  has been removed or never installed.
- A different deployment that exposes the same name pattern in a
  different physical location is genuinely indistinguishable from this
  one without richer signals — flag as `vendor_attribution_confidence:
  low` in any user-facing copy.

## Candidate Hypotheses

None confirmed; documented to aid future triangulation.

1. **Multi-zone alarm panel BLE bridge** — Honeywell, DSC, Bosch, or
   Visonic panels with an integrator's BLE add-on. Most plausible — the
   `Door<N>` naming scheme matches typical alarm-panel zone labelling.
2. **DIY ESP32 / nRF52 contact sensor** built from open-source firmware
   (ESPHome, Home Assistant). The ESPHome reference designs name their
   binary sensors by zone, and the trailing-space artifact would match
   a fixed-length name buffer.
3. **Industrial / commercial door-zone monitor** (warehouse roll-up
   doors, cooler doors, server-room access).

## How to verify (under 2 minutes)

1. **MAC OUI lookup** — find the device in nRF Connect on Android (iOS
   hides MACs) and resolve the OUI. Espressif / Nordic / Realtek OUIs
   are common DIY signals; a recognised alarm-panel OEM OUI would
   confirm the multi-zone-panel hypothesis.
2. **Active scan** — many firmwares put richer info in the scan
   response. "Door1 " might expand into "Door1 BedroomWindow" or
   similar.
3. **GATT connect** — read the Device Information Service (0x180A)
   characteristics for vendor / model / firmware. A `Manufacturer Name`
   string is definitive.

## References

- Export 17 capture: `research/adwatch_export 17.json`, three units
  (`Door1 `, `Door2 `, `Door4 `), 990 combined sightings on 2026-06-03.
- Companion vendor-unconfirmable fingerprint parsers:
  - `Unknown3E1D50CDParser`
  - `Unknown65333333Parser`
  - `UnknownD30F3C56Parser`
- Bluetooth Core Specification 5.4, Vol 3 Part C §11 — AD type
  `Complete Local Name (0x09)` formatting.
