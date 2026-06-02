# Dyson BLE-Only Lighting (Solarcycle / Lightcycle Morph)

## Overview

Dyson's task and floor lighting line uses a BLE-only control profile (newer
lamps drop the legacy WiFi+BLE Lightcycle protocol). Pairing happens once
through the MyDyson app; thereafter the lamp advertises continuously while
powered. All control (brightness, colour temperature, motion sensor, scenes)
sits behind an authenticated GATT connection — the advertisement itself is
identification only.

## Manufacturer

**Dyson Ltd.** — Malmesbury, UK / Singapore. Consumer appliances and
lighting (Solarcycle, Solarcycle Morph, Lightcycle, Lightcycle Morph).

## BLE Advertisement Structure

### Service UUIDs

| UUID | Family |
|------|--------|
| `2DD10010-1C37-452D-8979-D1B4A787D0A4` | Dyson BLE-only lights — primary service (Solarcycle Morph / E5R, others) |
| `9525AF9D-B772-4229-BBE3-41DCC7218167` | Dyson BLE-only lights — secondary advertising UUID (BWL7 generation) |

Either UUID is sufficient to identify a Dyson BLE-only light. Different
generations advertise different UUIDs, but each unit advertises one of the
two.

### Local Name Patterns

```
<MODEL>[-<REGION>]-<SERIAL>
```

| Field | Format | Example |
|-------|--------|---------|
| `MODEL` | Uppercase alphanumeric | `E5R`, `BWL7`, `CD06` |
| `REGION` | Optional 2-letter regulatory token | `US`, `EU`, `JP` |
| `SERIAL` | Uppercase alphanumeric, unit-specific | `SGA0791A`, `047262`, `ABC1234` |

Examples observed in the field:

- `E5R-US-SGA0791A` — Solarcycle Morph, US variant
- `BWL7-047262` — BWL7-generation floor light, region token elided
- `CD06-US-ABC1234` — original Lightcycle Morph, US variant (documented in
  community integrations)

### Known Model Codes

| Code | Product |
|------|---------|
| `CD06` | Lightcycle Morph (original WiFi+BLE) |
| `E5R` | Solarcycle Morph (BLE-only) |
| `BWL7` | Solarcycle Floor (BLE-only) |

Additional codes will appear as Dyson refreshes the line — they will share
the same advertising shape.

### Advertisement Behavior

- Advertises while the lamp is powered, regardless of on/off state.
- BLE 4.2 / 5.0 connectable advertisement.
- No manufacturer data, no service data — only the service UUID and the
  local name carry information.
- After cloud pairing the lamp accepts AES-128 + HMAC-SHA256 authenticated
  writes via GATT (long-term key issued by Dyson cloud during the one-time
  pairing flow).

## Identification

- **Primary**: either Dyson service UUID
  (`2DD10010-…` or `9525AF9D-…`)
- **Secondary**: local name matches `^(E5R|BWL7|CD06)-` (only known model
  codes — refuses to claim format-correct names with unknown prefixes to
  avoid false positives against other industrial naming schemes)
- **Device class**: `lighting`

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor identity | service UUID | Dyson |
| Model code | local name | `E5R`, `BWL7`, `CD06` |
| Product name | model code → table | "Solarcycle Morph (E5R)" etc. |
| Region / regulatory variant | local name | optional, when present |
| Serial number | local name | unit-specific, can be a stable identifier |

## What We Cannot Parse (requires GATT + cloud pairing)

- Power state (on / off)
- Brightness / colour temperature
- Motion-sensor state, ambient light reading
- Firmware version / hardware revision
- Pairing identity / cloud account binding

## Privacy Notes

The serial number is meaningful: Dyson uses it during cloud pairing to bind
the lamp to a user account, and it is etched on the product. A long-running
passive scan reveals which Dyson lamp models live in a residence — and the
naming convention preserves the unit's serial across reboots, so the
identifier is effectively static.

## Detection Significance

- Premium home / office task lighting nearby — consumer indoor environment.
- Multiple Dyson lamps with sequential serials suggest a single household or
  small office bulk purchase.
- Co-presence with other Dyson products (fans, purifiers) is common — those
  use different BLE profiles but the same MyDyson app.

## References

- `cmgrayb/hass-dyson` (Home Assistant integration covering the BLE-only
  light family) —
  <https://github.com/cmgrayb/hass-dyson>
  (see `custom_components/hass_dyson/const.py` and
  `.github/design/ble_lights.md` for the documented service UUIDs and the
  authenticated-GATT control flow)
- `alax/ha-dyson-lamps` (earlier HA integration, same UUID family) —
  <https://github.com/alax/ha-dyson-lamps>
- Dyson Solarcycle Morph product page —
  <https://www.dyson.com/lighting/desk-lamps/solarcycle-morph-cd06>
- Dyson serial-number format —
  <https://www.dyson.com/serial-number-help>
