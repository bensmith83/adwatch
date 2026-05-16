# Viper SmartStart (DEI Bluetooth Remote-Start Module)

## Overview

**Directed Electronics, Inc. (DEI)** — the company behind the Viper,
Python, Clifford, and Avital aftermarket car-security brands — ships
several Bluetooth Low Energy modules that bridge the vehicle's
remote-start / alarm system to the user's phone:

| Module | Product line | Notes |
|--------|--------------|-------|
| VSM50BT / VSM200 | Viper SmartStart Bluetooth | Original BLE remote start bridge |
| VSK100 | Viper SmartKey | Phone-as-key proximity unlock |
| DS4+    | Viper digital remote start | All-in-one BLE-only remote-start module |

The phone app talks GATT once paired, but the module advertises
continuously while a vehicle is parked so the phone can re-discover
the car when the driver approaches. The advertisement itself is
unencrypted and exposes the per-module serial number in the local
name — a stable, long-lived identifier for the installed vehicle.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xFFFF` | Reserved-for-testing / invalid usage by DEI |
| Service UUID | `B4520100-A308-4E56-8A52-536C2AD07147` | DEI proprietary primary service |
| Local name | `DEI-<7-or-8-digit-serial>` | e.g. `DEI-8580252` |

DEI's choice of company ID `0xFFFF` is non-compliant with the
Bluetooth SIG assigned-numbers spec (`0xFFFF` is reserved for
testing). The combination of name prefix `DEI-` *and* either the
DEI service UUID *or* the `0xFFFF` company ID is a reliable signal:
no other commercial product known to adwatch shares both.

## Wire Format (real-world capture)

```
Local name: "DEI-8580252"
Mfr data:   ff ff 06 0a 50 0a 46
            └─┬─┘ └──────┬──────┘
             cid    payload (5 bytes, opaque)
Svc UUIDs:  [B4520100-A308-4E56-8A52-536C2AD07147]
```

| Offset (post-cid) | Bytes        | Meaning |
|-------------------|--------------|---------|
| 0                 | `06`         | Likely protocol / message-type byte |
| 1                 | `0A`         | Status flags (battery? alarm armed?) |
| 2–4               | `50 0A 46`   | Opaque (frame counter? rolling code?) |

The 5-byte payload changes between adv intervals (rolling-code
behavior expected from automotive remote-start hardware), so the
parser does not attempt to decode it — it is captured verbatim as
`payload_hex` for forensic comparison.

The local-name serial (`8580252`) is fixed per module and matches the
serial printed on the bottom of the VSM/DS-series enclosure. This
serial is what the SmartStart cloud account uses to bind a vehicle to
a user.

## Identity Hashing

```
identifier_hash = SHA256("viper_smartstart:{serial}")[:16]
```

The 7-or-8-digit serial in the local name is sufficient to identify a
specific physical vehicle install (it does not rotate). MAC address
also stays stable across reboots based on the captures observed.

## Privacy Note

Because DEI broadcasts the per-module serial in plaintext, anyone
within ~30m of a parked vehicle with Viper SmartStart can:

1. Identify that the vehicle has a Viper remote-start kit installed
2. Track the specific vehicle across locations / time via the serial
3. Correlate the serial back to a SmartStart account if the owner's
   account is known (the cloud API uses the same serial as primary
   key)

This is comparable to BLE TPMS sensors or older BLE tile-trackers —
not a vulnerability per se, but worth noting in the surveillance
profile.

## What We Cannot Parse Without GATT

- Lock state (armed / disarmed)
- Engine running state
- Battery voltage
- Cabin temperature (DS4+ only)
- Rolling-code authentication state

The GATT layer requires an authenticated session against the DEI
service UUID and is out of scope for adwatch's passive scanner.

## References

- DEI / Viper SmartStart product page: https://viper.com/smartstart
- VSM50BT manual: https://www.directeddealers.com/manuals/OG/Viper/QRGVSM50BT%202012-05%20web.pdf
- VSM50BT Bluetooth module: https://viper.com/smartstart/product/vsm50bt/viper-smartstart-bluetooth-module
- Bluetooth SIG `0xFFFF`: reserved for testing (non-compliant assignment)
