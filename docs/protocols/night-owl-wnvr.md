# Night Owl WNVR-BTWN8 Series — Bluetooth NVR

## Overview

Night Owl's Bluetooth Wi-Fi NVR line (10-channel security-camera hub,
app-paired setup) broadcasts a BLE advertisement whose local name
identifies the exact product line. Independently corroborated via an
exact FCC-ID string match: **2APRB-WNVR-BTWN8**.

## Fingerprint

### Local Name

| Pattern | Notes |
|---------|-------|
| `NO_WNVR-<model>` | `NO_` = Night Owl; e.g. `NO_WNVR-BTWN8-V2` |

### Manufacturer Data — no real company-ID field

The app decodes company ID `0x3033` from the first two manufacturer-data
bytes, but this is an **artifact, not a real vendor signal**: the entire
manufacturer-data blob is pure printable ASCII end to end. `0x3033` is
just the ASCII digits `"0"` + `"0"` read as a little-endian CID. The
parser's real anchor is the local-name prefix plus "the whole payload
decodes as printable ASCII" — never gate on the CID as if it were a real
company identifier.

Observed shape (sweep 2026-07-17, n=1 distinct value):

```
301b976be7b8_71FJ8MOAV0ZM_0
└────┬─────┘ └─────┬─────┘ │
 12-hex, MAC-  pairing/     revision
 like segment  serial token digit
```

Read as a headless-NVR BLE provisioning beacon (MAC-as-text + a token the
companion app uses to identify/claim a specific unit during Wi-Fi setup).
Field boundaries beyond the raw string are unconfirmed — only one distinct
payload value has been observed, across 2 sightings of what appears to be
one physical unit.

## Identification

- **Primary**: local name `NO_WNVR*` + manufacturer data that decodes
  fully as printable ASCII.
- **Device class**: `security_camera`.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Night Owl` |
| Product line | hard-coded | `WNVR-BTWN8` |
| `ascii_payload` | manufacturer data, decoded | raw string, structure unconfirmed |

## What We Cannot Parse

- Individual field boundaries within the ASCII payload (n=1 sample).
- Recording state, camera count/status, Wi-Fi pairing progress.

## Stable Identity

No confirmed per-unit identifier separate from the MAC. Anchored on
`stable_key = night_owl_wnvr:<mac>`.

## References

- FCC ID `2APRB-WNVR-BTWN8` (fcc.report / fccid.io) — confirms the
  `WNVR-BTWN8` product-line string.
- Night Owl's current product listing for the `BTWN8` collection.
