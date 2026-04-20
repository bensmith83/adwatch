# Beta Bionics iLet Bionic Pancreas Protocol

## Overview

The **iLet** is an FDA-cleared (510(k) K222516, K223846, K231485 — most
recent May 2023) automated insulin delivery (AID) pump from **Beta Bionics,
Inc.** It pairs via Bluetooth Low Energy with:

- The **iLet mobile app** (Android package `com.betabionics.ilet`)
- Dexcom G6 / G7 continuous glucose monitors (over BLE)
- FreeStyle Libre 3 Plus sensors (over BLE)

The iLet is a true **medical device** — mis-identification would be a
compliance hazard, so we parse it conservatively: name pattern OR exact
vendor service UUID.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `A0090101-0605-0403-0201-F0E0D0C0B0A0` | 128-bit; observed in the wild |
| Local name | `iLet4-<4hex>` | `iLet4` is the current hardware revision |
| Device class | `medical_device` | |

### Note on the Service UUID

The 128-bit UUID looks like a hand-picked placeholder rather than a randomly
generated one. The trailing bytes are a descending count:

```
a0 09 01 01 - 06 05 04 03 - 02 01 - f0 e0 d0 c0 b0 a0
                \_______/   \___/   \______________/
                 6-5-4-3    2-1     f-e-d-c-b-a stepped
```

Real UUIDs don't do that. Whether this is Beta Bionics shipping a test
UUID in production, or a UUID they genuinely chose, we accept it as-is
because it's what the real hardware transmits.

## Ad Format

The advertisement is primarily a connection invitation. Actual therapy
data (insulin dose, CGM readings, bolus history) lives behind a paired
GATT session and is not visible passively.

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service UUID | iLet nearby |
| Hardware revision | local_name prefix | e.g. `iLet4` |
| Device suffix | last 4 hex of name | Stable per unit |

### What We Cannot Parse

- Insulin dose / bolus events
- CGM glucose readings
- Battery level / reservoir volume
- Firmware version
- Patient profile data
- Pairing PIN

## Identity Hashing

Prefer the **device suffix** over the outer BLE MAC (the pump may use a
random resolvable address for privacy):

```
if name matches iLet<N>-<suffix>:
    identifier = SHA256("{suffix}:ilet")[:16]
else:
    identifier = SHA256("{mac}:ilet")[:16]
```

## Detection Significance

- Indicates a person living with Type 1 diabetes in range
- **Privacy-sensitive** — treat sightings with the same care as a CGM
  or other medical device

## Parsing Strategy

1. Match on local-name regex `^iLet\d+-[0-9A-Fa-f]{4}$` OR service UUID
   `a0090101-0605-0403-0201-f0e0d0c0b0a0`.
2. Extract hardware revision + 4-hex suffix from the name if present.

## References

- [Beta Bionics iLet User Guide (LA000154_B)](https://www.betabionics.com/wp-content/uploads/LA000154_B_iLet-User-Guide.pdf)
- [iLet Mobile App pairing steps (Beta Bionics)](https://www.betabionics.com/user-resources/ilet-app-pairing-steps/)
- [FDA 510(k) K231485 summary](https://www.accessdata.fda.gov/cdrh_docs/pdf23/K231485.pdf)
- [iLet Mobile App on Google Play](https://play.google.com/store/apps/details?id=com.betabionics.ilet)
