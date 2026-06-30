# Hilton Connected Room in-room controller

## Overview

**Hilton Connected Room** is Hilton's guestroom-automation platform: an
in-room controller / edge box lets the **Hilton Honors** mobile app drive
the room's thermostat, TV, lights, and window drapes. The controller
advertises a vendor-allocated 128-bit BLE service UUID that the app's
**"CR Connector"** module (`com.hilton.cr.crconnector` — *Connected Room
Connector*) connects to.

Announced in 2017 and rolled out across Hilton-brand properties from 2018,
Connected Room is built on top of third-party in-room hardware (Honeywell
INNCOM, Verdant/Copeland thermostats; LG / Samsung hospitality TVs). The
BLE advertiser is the **room's automation hub**, not the door lock — Hilton
**Digital Key** is a separate subsystem in the same app.

Each controller sets its GAP local name to the **hotel room number**, so a
scan in a Hilton property surfaces the room numbers of nearby guestrooms — a
strong place fingerprint and a mild privacy signal.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `8EC1E808-67C9-11E6-8B77-86F30CA893D3` | Vendor-allocated 128-bit; the decisive anchor |
| Local name | room number, `^\d{3,4}$` | e.g. `610`, `213`, `1208` — floor + room |
| Manufacturer data | none | — |
| Address type | `random` | rotating; room number is the stable identity |

**The service UUID alone is sufficient.** It is globally unique and
vendor-allocated; its only known public occurrence is the Hilton Honors app
(below), so false positives are effectively impossible. The local name is a
confirmer and the field we surface.

### Why this UUID = Hilton (attribution)

`8EC1E808-67C9-11E6-8B77-86F30CA893D3` appears, lowercased, as a hard-coded
constant in the **decompiled Hilton Honors Android app**, under
`com/hilton/cr/crconnector/core/constant`, as the **first/primary entry** of
a 21-UUID Connected Room GATT table (alongside a `b31e89de-…` vendor service
and the standard `0000180a` Device Information Service). The package path
`com.hilton.cr.crconnector` = "Connected Room Connector".

The UUID is itself a **UUIDv1** whose time/version field `67C9-11E6` decodes
to **~2016** — exactly when Hilton was building Connected Room. The
attribution and the timeline are self-consistent.

The hardware OEM of the controller box is intentionally **not** claimed: the
`b31e89de` vendor base did not resolve to any public manufacturer, and the
only confirmed OEMs (Honeywell INNCOM, Verdant) are the *thermostats*, not
the BLE hub.

### Local-name decode

Names are hotel room numbers — leading digit(s) = floor, last two = room
slot on that floor:

| Local name | Floor | Unit |
|---|---|---|
| `610` | 6 | 10 |
| `213` | 2 | 13 |
| `308` | 3 | 08 |
| `1208` (4-digit) | 12 | 08 |

Observed cluster (one capture): 208, 210, 213, 308, 310, 410, 508, 512, 609,
610, 708, 810 — floors 2–8, rooms 08–13: a tight multi-floor wing of one
property, 12 controllers = 12 nearby guestrooms.

### What we can surface

| Field | Source | Notes |
|---|---|---|
| `vendor` | hard-coded | `Hilton` |
| `product` | hard-coded | `Connected Room controller` |
| `device_type` | hard-coded | `guestroom automation hub` |
| `room_number` | localName | when name matches `^\d{3,4}$` |
| `floor` | localName | leading digit(s) (all but last two) |
| `unit` | localName | last two digits |

### What we cannot surface

- Thermostat setpoint / mode, TV state, light/drape state — all controlled
  over an authenticated GATT connection we never make.
- The controller's hardware OEM (not advertised; vendor base unresolved).

## Parser scope (passive only)

Presence + room number only. NearSight never connects; all control traffic
is GATT-only behind app authentication.

## Stable identity

```
stable_key = hilton_connected_room:room:<room_number>   (name present)
stable_key = hilton_connected_room:mac:<mac>            (name absent)
identifier = SHA256(stable_key)[:16]
```

The room number is stable per controller and survives the random-address
rotation (one controller per room).

## Detection significance

- Presence of these controllers ⇒ you are inside a **Hilton-brand Connected
  Room property**, and the cluster effectively **maps the room numbers of
  nearby guestrooms** (floor + unit) — a strong location fingerprint.
- Mild privacy signal worth flagging: a passive scanner can enumerate which
  rooms around you are occupied/equipped.
- The unique 128-bit UUID gate keeps attribution honest — no collision with
  the door-lock / Digital Key subsystem or unrelated devices.

## References

- [Decompiled Hilton Honors app — `crconnector` UUID constant table](https://github.com/taciturnaxolotl/hilton-honors/blob/8165b01ce90fe982f455d6387dd7329d3baf902a/smali_classes3/com/hilton/cr/crconnector/core/constant/a.smali) — exact UUID + full Connected Room GATT table
- [Hilton's Connected Room overview](https://hospitalitytech.com/hiltons-connected-room-gives-guests-control-mobile-app)
- [Verdant/Copeland — Hilton Connected Room thermostat integration](https://verdant.copeland.com/hilton-connected-room/)
- [Honeywell INNCOM PC-502.H product guide (Connected Room module)](https://prod-edam.honeywell.com/content/dam/honeywell-edam/hbt/en-us/documents/literature-and-specs/brochures/inncom/hbt-bms-PC-502-H-PRODUCT-GUIDE.pdf)
- Captures: `research/nearsight_export 7.json` (12 controllers, ~192 sightings).
