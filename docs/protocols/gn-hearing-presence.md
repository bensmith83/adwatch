# GN Hearing Presence Beacon (FD20)

## Overview

**GN Hearing A/S** (a subsidiary of GN Store Nord — sister company of
GN Netcom / Jabra audio) holds SIG service-UUID `0xFD20` (plus siblings
`0xFD71` and `0xFEFE`) for its hearing-aid product portfolio:
**ReSound** (premium hearing aids), **Beltone** (mid-tier), **Interton**
(entry-tier), and **Jabra Enhance** (OTC).

The captured signature — `FD20:01` service data, no other BLE signal —
is the **smartphone companion-app presence beacon**, not the hearing
aid itself. When the companion app (ReSound Smart 3D, Beltone HearMax,
Jabra Enhance, Smart-Remote, etc.) is foregrounded or in
background-scan mode, it advertises the GN service UUID so a paired
hearing aid scanning nearby can wake up and reconnect — a common
GATT-reconnection pattern.

We saw **93 distinct rotating-address devices** producing this signature
across 8 exports (909 total sightings) — the largest single
unattributed signature in our 20-export corpus. That count is
inconsistent with the devices being hearing aids themselves (no
environment plausibly has 93 hearing-aid wearers in passive capture),
but fits well with phones running GN companion apps.

## Distinguishing Smartphone vs Hearing-Aid

The parser sets `device_class` based on whether the FD20-family UUIDs
appear in the advertised `serviceUUIDs` list:

| `device_class` | Triggers when | Likely source |
|---|---|---|
| `hearing_ecosystem` | FD20 only in `serviceData` | smartphone running a GN companion app |
| `hearing_aid` | FD20, FD71, or FEFE in `serviceUUIDs` | the hearing aid itself |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service-data key | `0xFD20` | GN Hearing A/S — SIG-registered |
| Service-data payload | exactly `0x01` (1 byte) | likely a protocol-version byte |
| Service UUIDs | `[]` *(presence)* OR `[FD20]` / `[FD71]` / `[FEFE]` *(hearing aid)* | see device-class table |
| Manufacturer data | *(absent)* | |
| Local name | *(absent)* | |
| Address type | `random` | privacy-rotating BD_ADDR |

### Strict Payload Gate

The parser requires the FD20 service-data payload to be exactly
`0x01` (1 byte). Future GN frames with different payloads are deferred
to a future parser variant — they represent different beacon subtypes,
not the same one.

### What We Can Surface

| Field | Source | Notes |
|---|---|---|
| Vendor | hard-coded | `GN Hearing A/S` |
| `sig_service_uuid` | hard-coded | `0xfd20` |
| `payload_version` | service-data | `0x01` |
| `likely_source` | derived | `smartphone_companion_app` or `hearing_aid_device` |
| `companion_apps` | hard-coded | `ReSound Smart 3D, Beltone HearMax, Jabra Enhance, Smart-Remote` |
| `brands` | hard-coded | `ReSound, Beltone, Interton, Jabra Enhance (OTC)` |

### What We Cannot Surface from the Advertisement

- Specific hearing-aid model (ReSound Nexia vs Vivia vs ONE vs OMNIA;
  Beltone Imagine vs Achieve vs Boost Max; …).
- Live hearing-aid state (battery, volume, program, streaming source).
- Fitness data / step count (newer hearing aids expose this via GATT).
- Pairing state.
- Wearer identity / audiogram.

All live state lives behind GATT on the hearing aid's vendor service
(undocumented).

## Stable Identity

The advertisement carries no per-device payload bits, so the
identifier is anchored on the rotating BD_ADDR. Distinct phones will
rotate to new MACs over time and appear as fresh identities — that's
intentional and matches the privacy intent of the companion app's
design.

```
stable_key = gn_hearing_presence:<bd_addr>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- The `hearing_ecosystem` (smartphone) variant strongly suggests **a
  GN hearing-aid wearer is nearby** — the companion app only
  advertises FD20 when paired with at least one GN aid. Has weak
  health-PII implications similar to other accessibility-device
  detection.
- The `hearing_aid` variant means the device itself is in range — a
  real GN aid passing by. Treat with health-PII care: scrub before
  any third-party / AI-provider upload per the project's redaction
  policy at the upload boundary.
- Large-environment counts (93 devices over the captures) are normal
  for the smartphone variant — they don't imply mass hearing-aid
  presence.

## Sibling Parsers

- `JabraParser` covers GN Netcom (Jabra audio headsets) — explicitly
  excludes FD20/FD71 from its routing because those are GN Hearing
  service UUIDs, not GN Netcom.

## References

- [BT SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFD20` → GN Hearing A/S
- [GN Group corporate (brand portfolio)](https://www.gn.com/about/gn-group)
- [ReSound Smart 3D app](https://www.gnhearing.com/en/products/apps/smart-3d-app)
- [Android ASHA spec (uses `0xFDF0`, not FD20)](https://source.android.com/docs/core/connect/bluetooth/asha) — confirms FD20 is distinct from the ASHA presence beacon
