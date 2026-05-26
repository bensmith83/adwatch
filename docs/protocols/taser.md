# TASER (Axon Enterprise consumer self-defense)

## Overview

Axon Enterprise (formerly TASER International) ships consumer
self-defense devices that pair with a phone over BLE so the app
can dispatch help when the weapon is fired.

Two consumer SKUs have shipped with Bluetooth:

| Model | Years | Companion app | Status |
|-------|-------|---------------|--------|
| TASER Pulse+ | 2018–2024 | Noonlight | Discontinued 2022-04-08. Noonlight pairing ended 2024-04-01; Noonlight app sunset 2024-05-31. |
| TASER Bolt 2 | 2022– | Axon Protect | Current. Adds GPS tracking + auto-dispatch on discharge. |

(TASER Pulse 2 — note the "+" — has *no* Bluetooth. Don't confuse
with Pulse+.)

We've reverse-engineered the Pulse+ from a captured GATT trace.
The Bolt 2 likely shares the same firmware base (same vendor, same
MCU family, same product line) but this has not been confirmed and
specific service UUIDs may differ. The parser is permissive enough
to catch Bolt 2 if it advertises the same GAP name and OUI; it
should be tightened or split once we capture one.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | *(none)* | Axon has no SIG-assigned company ID; manufacturer data does not route. |
| MAC OUI | `00:25:DF` | IEEE block assigned to Axon Enterprise, Inc. (Scottsdale AZ). Public address, stable per unit. |
| GAP local name | `TASER` | Exact uppercase, 5 chars. Read from `0x2A00` Device Name characteristic; also the Manufacturer Name (`0x2A29`). |
| Appearance | `0x0200` Generic Tag | Read from `0x2A01`. Not distinctive on its own. |
| Service UUIDs | `b7508330-4b0a-11e3-8f96-0800200c9aXX` | Vendor-allocated 128-bit family. Observed `XX` range 0x64..0x88 (services and characteristics share the base, only the trailing byte varies). |
| Service UUID | `9e5d1e47-5c13-43a0-8635-82ad38a1386f` | Companion service, suspected OTA / firmware update channel. |

We require ≥2 signals before claiming a match (name + OUI, name +
custom UUID, or OUI + custom UUID). `TASER` alone is too cheap a
GAP name; OUI `00:25:DF` alone is also too generic — that block is
shared with Axon body cams, dock stations, fleet hardware, etc.

## Serial Number

Read from `0x2A25` Serial Number String. Observed format: a
single letter prefix + 8 digits, e.g. `X87004693`. The `X` prefix
is documented by Axon for civilian-line serials; the digits encode
the unit's identity. Not available passively — requires a GATT
connection.

## Firmware / Hardware

| Characteristic | Value | Notes |
|---|---|---|
| `0x2A26` Firmware | `04.02.0112030D1438` (Pulse+, 2021 capture) | Opaque; format probably is `<major>.<minor>.<build-blob>`. |
| `0x2A27` Hardware | `17` | Single integer, board rev. |
| `0x2A24` Model | `1` | One-digit model, not human-meaningful. |
| `0x2A23` System ID | `00-25-DF-FF-FE-44-2E-C8` | EUI-64 derived from MAC by the standard FF:FE insertion. Confirms public address; no extra entropy. |

## GATT Layout (Pulse+)

The device exposes both standard SIG services and proprietary
ones. Standard services are present primarily as a transport
trick — most notable is Heart Rate (`0x180D`), which Pulse+
re-uses as a generic notify channel; it is **not** a heart-rate
monitor. This pattern is consistent with the Noonlight Bluetooth
Plugin SDK approach, where vendors expose a small set of standard
characteristics so the Noonlight mobile SDK can talk to any
integrated device without per-vendor code paths.

```
0x1800 Generic Access            — Device Name, Appearance
0x1801 Generic Attribute
0x180A Device Information        — Firmware, Hardware, Manufacturer,
                                    Model, Serial, System ID
0x180D Heart Rate (phantom)      — Repurposed notify channel; the
                                    device is not a heart-rate monitor
0x181C User Data                  — First Name, Last Name, Gender
                                    (owner identity bound via the app)
0000aaa0-0000-1000-8000-aabbccddeeff
                                  — Proprietary service, custom
                                    `aabbccddeeff` base (non-SIG, not
                                    the SIG base ending `00805f9b34fb`)
b7508330-4b0a-11e3-8f96-0800200c9a64..88
                                  — Vendor-proprietary services /
                                    characteristics family
9e5d1e47-5c13-43a0-8635-82ad38a1386f
                                  — Companion proprietary service
                                    (suspected OTA)
```

Notable: the `0800200c9aXX` tail is a well-known JavaScript-era
UUID base from the early 2010s. Axon picked it up as a vendor-base
and allocates services / characteristics by incrementing the last
byte.

## Identity Hashing

```
stable_key      = "taser:" + mac_address
identifier_hash = SHA256(stable_key)[:16]
```

The Pulse+ uses a public BLE address (drawn from Axon's IEEE OUI
block), so the MAC is stable across sessions and is the right key
for cross-session identity. The GAP local name `TASER` is shared
across all units, so don't key off it.

## What We Can Parse Passively

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | OUI `00:25:DF` + name `TASER` | Axon Enterprise (high confidence with ≥2 signals). |
| Product family | UUID + name | "TASER consumer (Pulse+/Bolt 2)" — cannot distinguish models from advertisement. |
| Per-unit identity | MAC | Stable; public address. |

## What Requires GATT

- Serial number (`X87004693` etc.)
- Firmware / hardware revisions
- Cartridge state, charge level, discharge events
- Owner identity bound to the User Data service
- Any control plane (the `b7508330-...c9a85`/`c9a87` writeable
  characteristics + paired `c9a86`/`c9a88` notifies look like a
  command/response channel)

## What Requires the Vendor App / Cloud

- Auto-911 dispatch on weapon discharge — handled by the Noonlight
  (Pulse+, EOL) or Axon Protect (Bolt 2) cloud workflow.
- GPS location of the *paired phone* at discharge time — phone
  GPS, not weapon GPS.

## Threat Model Notes

Detection of a TASER advertisement near you is a meaningful safety
signal (someone has a TASER paired to a nearby phone). The
advertisement is broadcast continuously while the device is
powered and not currently connected; it's visible to any BLE
scanner within range (~10–30m depending on environment).

The signal does **not** indicate the weapon has been fired —
discharge state is only visible via the GATT control plane or
via the vendor's cloud workflow, neither of which is accessible
to a passive observer.

## References

- IEEE OUI registry: `00-25-DF` → Axon Enterprise, Inc.
  (17800 N 85th St, Scottsdale AZ 85255, US)
- Axon press release, 2018-11-14: "TASER Self-Defense Launches
  First Consumer TASER Device to Notify 911 When Deployed;
  Announces Partnership with Connected Safety Company Noonlight"
- Axon press release, 2022-01-18: "Axon Announces New Consumer
  TASER Device That Alerts Emergency Dispatch When Fired"
  (introduces Bolt 2 + Axon Protect)
- Noonlight Help Center: "End of Support for TASER Pulse+"
  (Pulse+ unpaired 2024-04-01; app sunset 2024-05-31)
- Captured GATT trace: nRF Connect, 2021-08-09, Pulse+ s/n
  `X87004693`, fw `04.02.0112030D1438`, MAC `00:25:DF:44:2E:C8`
