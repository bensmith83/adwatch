# ASSA ABLOY Aperio Wireless Lock

## Overview

ASSA ABLOY Aperio is a family of battery-powered wireless locks, escutcheons,
and door sensors used in commercial access-control installations. The locks
communicate over a proprietary BLE GATT profile, with Aperio communication
hubs (e.g. AH30) acting as the bridge between the locks and the host
access-control system (e.g. Brivo, Genetec, AMAG).

## Manufacturer

**ASSA ABLOY AB** — Stockholm, Sweden / Göteborg manufacturing. ASSA ABLOY is
one of the world's largest lock and security-hardware companies (HID Global,
Yale, Mul-T-Lock, Aperio are all part of the group).

## BLE Advertisement Structure

### Service UUIDs

| UUID | Description |
|------|-------------|
| `00009800-0000-1000-8000-00177A000002` | Aperio proprietary service (base embeds the ASSA ABLOY IEEE OUI `00:17:7A`) |

The OUI substring `00177A` inside a 128-bit BLE service UUID is the family
"tell". ASSA ABLOY reuses its registered OUI in the UUID base across the
Aperio line, which makes the identification check robust even when the local
name is missing or has been customised.

### Local Name Patterns

| Pattern | Likely role |
|---------|-------------|
| `AI<NNN>` | Aperio lock / cylinder unit (e.g. `AI118`) |
| `EI<NNN>` | Aperio escutcheon / sensor unit (e.g. `EI101`, `EI102`) |

The two-letter prefix is the model-family code and the digits are the unit
identifier — useful for distinguishing units within a single installation. The
prefix-to-product-family mapping needs lab confirmation; the field captures
that drove this parser saw `AI` and `EI` prefixes co-broadcasting from the
same site, which is consistent with paired cylinder+sensor or hub+lock pairs
typical in Aperio deployments.

### Advertisement Behavior

- The advertisement carries only the service UUID and a short local name — no
  manufacturer data, no service data payload.
- The real control surface (auth handshake, lock/unlock, status, key
  provisioning) is behind authenticated GATT writes after pairing.
- Aperio devices are battery-powered, so they typically use connectable
  advertising at a low duty cycle while idle and a higher rate after a
  user-presented credential wakes them.

## Identification

- **Primary**: service UUID `00009800-0000-1000-8000-00177A000002`
- **Secondary**: local name matching `^[AE]I\d{3,}$`
- **Device class**: `access_control`

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor identity | service UUID | ASSA ABLOY Aperio |
| Model family code | local name | `AI` (lock) / `EI` (escutcheon/sensor) |
| Unit identifier | local name | digits — useful for keeping a stable site map |
| Device presence + location | RSSI + identifier hash | site mapping over time |

## What We Cannot Parse (requires GATT)

- Lock state (locked / unlocked / forced / propped)
- Battery level
- Firmware version / hardware revision
- Credentials, key tables, audit trail (encrypted)
- Door open / motion-sensor state

## Privacy & Security Notes

Aperio is commercial access-control hardware — sightings indicate doors or
cabinets in a building, not consumer locks. The advertisement does not leak
state, but a long-running scan can profile a site's lock count and rough
layout from RSSI alone.

## Detection Significance

- Commercial / enterprise access-control deployment nearby (office, hospital,
  data center, hotel back-of-house, lab).
- Co-located `AI*` and `EI*` units suggest a multi-door Aperio site rather
  than a one-off door.
- Brivo, Genetec, AMAG, Lenel, and HID front-ends often sit upstream of
  Aperio hardware; co-presence with an HID/Brivo reader strongly suggests an
  ASSA ABLOY access-control installation.

## References

- ASSA ABLOY Aperio product page —
  <https://www.assaabloy.com/group/en/products/access-control/wireless-solutions>
- Brivo "ASSA ABLOY Aperio Configuration Guide" —
  <https://resources.brivo.com/configuration-guides/assa-abloy-aperio-configuration-guide>
- IEEE OUI `00:17:7A` — ASSA ABLOY AB
  (<https://maclookup.app/macaddress/00177A>)
- Brivo Mobile SDK (uses the same Aperio service UUID for GATT discovery) —
  <https://github.com/brivo-mobile-team/brivo-mobile-sdk-ios>
