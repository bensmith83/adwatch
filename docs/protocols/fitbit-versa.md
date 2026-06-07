# Fitbit Versa / Sense / Air (FD62 Service-UUID-Only Advertisement)

## Overview

Modern Fitbit smartwatches and trackers — **Versa 2/3/4, Sense, Sense 2,
Inspire 2/3, Charge 5/6, Luxe, Ace 3/LTE**, plus the 2026 Google-branded
**Air** pebble — emit a minimal BLE advertisement that contains **only**
a 16-bit service UUID (`FD62` or the newer `FD63`) and the device's local
name (e.g. `Versa 4`, `Google Fitbit Air`). There is no manufacturer data
block — distinct from the older Fitbit Charge / Inspire trackers, which
use company ID `0x000A` with a 2-byte opcode + device-type payload (see
`fitbit.md`).

`0xFD62` and `0xFD63` are Fitbit's BT-SIG-assigned 16-bit service UUIDs
("Member service UUID, Fitbit, Inc."). Any device advertising either UUID
is a Fitbit product.

This parser covers the FD62/FD63 family; the original `FitbitParser`
continues to handle the mfr-data variant.

## Supported Models

| Local name family       | Hardware |
|-------------------------|----------|
| `Versa`                 | Original Versa (sometimes still seen) |
| `Versa 2/3/4`           | Versa 2 / 3 / 4 |
| `Sense` / `Sense 2`     | Sense / Sense 2 |
| `Inspire` / `Inspire 2/3` | Inspire band family |
| `Charge` / `Charge 5/6`  | Charge band family |
| `Luxe`                  | Luxe band |
| `Ace` / `Ace 3`         | Kids' Ace family |
| `Google Fitbit Air` / `Air` | "Air" variant — observed in capture, product attribution not independently verified |

The parser does not hard-code this list — it accepts any name that
matches `^(?:Google Fitbit )?(Versa|Sense|Inspire|Charge|Luxe|Ace|Air)( \d+)?$`.
The optional `Google Fitbit ` brand prefix was added when an FD62 capture
with local name `Google Fitbit Air` appeared in
`research/nearsight_export 3.json`; FD62 itself is enough to attribute the
vendor.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FD62` (16-bit) | Fitbit, Inc. SIG assignment |
| Local name | `Versa N`, `Sense N`, … | Stable, identifies model |
| Manufacturer data | — | Absent (key distinguishing feature from Charge / Inspire) |

A reliable match is **service UUID `FD62` AND a matching local name**.
FD62 alone is enough to identify as "Fitbit product" but not the
specific model — the name is what disambiguates Versa from a future
Inspire variant that may migrate to the same service UUID.

## Wire Format (real-world capture)

```
Local name: "Versa 4"
Mfr data:   (none)
Svc UUIDs:  [FD62]
```

That's the entire advertisement. All device state (heart rate,
notifications, sync status, battery) is delivered via paired GATT
sessions, not in the advertisement.

## Identity Hashing

```
identifier_hash = SHA256("fitbit_versa:{model}:{mac_address}")[:16]
```

Modern Fitbit watches **do rotate** their BLE MAC at the OS-controlled
interval when unpaired, but a paired watch holds a Resolvable Private
Address that's stable to the paired phone. From a passive scanner's
perspective the MAC may rotate every ~15 minutes; the local name is
the only persistent identifier.

If MAC rotation is observed in a capture session, multiple identifier
hashes per physical watch is the expected outcome. The
`stableKey = model` field allows downstream collapse to "a Versa 4
nearby" if the user wants per-model rather than per-MAC granularity.

## What We Cannot Parse Without GATT

- Heart rate (live)
- Step count / activity rings
- Battery percent
- Sleep state
- Sync state with the phone
- Watch faces / notifications

All of those require a paired GATT session against the Fitbit-
proprietary service characteristics, which are encrypted post-pairing
and out of scope for adwatch's passive scanner.

## References

- BT SIG 16-bit UUID `0xFD62` → Fitbit, Inc.
- Fitbit Versa 4 product page: https://www.fitbit.com/global/us/products/smartwatches/versa
- Sibling parser (older mfr-data Charge / Inspire): `fitbit.md`
