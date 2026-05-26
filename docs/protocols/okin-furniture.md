# OKIN Refined Power (Motorized Furniture)

## Overview

OKIN Refined Power (a DewertOkin subsidiary) is the dominant OEM
behind motorized adjustable beds, power recliners, and lift
chairs. Their `JLDP`-series control boxes ship inside furniture
sold under La-Z-Boy, Tempur-Pedic, Lucid, Serta, Enso, Flexabed,
Pride Mobility, and dozens of other rebrands. The companion app
(`OkinComfortBed` / `OkinComfortBed II`) pairs over BLE.

The advertisement is **name-only** — no manufacturer-data, no
service-data, no service UUIDs in the ad payload. Everything
dynamic (head angle, foot angle, under-bed light, massage) lives
behind GATT service `0000FFE0-…` and requires a paired connection.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `OKIN-BLE<8 decimal digits>` | The only signal in the advertisement |

The 8 digits are a **zero-padded decimal serial**, not hex and not
a MAC tail. Example: `OKIN-BLE00018255` is unit serial 18,255.
Leading zeros are preserved as a string — don't parse to int and
re-format.

## Wire Format

No payload to decode. The local name is the entire signal.

```
OKIN-BLE 0 0 0 1 8 2 5 5
└───┬──┘ └──────┬──────┘
    │           └── zero-padded decimal serial (8 chars)
    └── product-line prefix (constant)
```

## Identity Hashing

```
identifier_hash = SHA256(serial)[:16]
```

The bed/chair never moves, but its BLE MAC may rotate. The serial
in the local name is stable per physical unit and is the right key.

## Product Family

| Component | SKU prefix | Role |
|-----------|------------|------|
| Control box | `JLDP.xx.xxx.xxx` (e.g. `JLDP.03.006.000`, `JLDP.05.046.001`) | The thing that advertises BLE |
| Handset / remote | `JLDK.xx.xx` (e.g. `JLDK-18-01`) | Wired or RF — does NOT advertise BLE |

The advertisement can't distinguish bed from chair — both use the
same control-box family. `device_class = motorized_furniture` is
the most specific class we can claim from a passive scan.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | name prefix | OKIN Refined Power |
| Product family | name prefix | OKIN JLDP control box |
| Serial | name suffix | 8-digit decimal string |

## What Requires GATT Connection

- Head angle (FFE4 notify, bytes 3–4, raw / 16000 × 60°)
- Foot angle (FFE4 notify, bytes 5–6, raw / 12000 × 45°)
- Massage state / timers
- Under-bed light state
- Motor-running inference

Commands are written to service `0000FFE5-…` characteristic
`0000FFE9-…` per the `smartbed-mqtt` protocol notes.

## References

- `richardhopton/smartbed-mqtt` — issue #53 documents the OKIN
  BLE protocol (the only public reverse-engineering reference)
- OkinComfortBed II on the iOS App Store
- OKIN Comfort Bed on Google Play
- FCC filings for `JLDK-18-01` (OKIN Refined Electric Technology)
- `kristofferR/ha-adjustable-bed` discussion #249 (Lucid L600
  identification as OKIN-based)
