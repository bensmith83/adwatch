# Lovense BLE Personal-Wellness Device

## Overview

Lovense is a well-known manufacturer of BLE-connected personal wellness /
intimacy devices. The product line has gone through three protocol
generations, each using a different BLE service-UUID family but a
consistent local-name convention so client software can recognize the
brand across hardware revisions. Lovense's BLE protocol has been
extensively reverse-engineered by the open-source community
(notably the [buttplug.io](https://buttplug.io/) project) — adwatch's
attribution leans on their published specification.

## Identification

Two signals must both match before adwatch attributes a Lovense
device:

1. **Local name** starts with `LVS-` (current convention) or `LOVE-`
   (legacy first-generation), followed by a 1-or-more-letter model
   code and a 2-to-4-digit firmware-hint suffix.
2. **A service UUID** from one of the three protocol generations
   appears in the advertisement.

```
local_name: LVS-J0123        LVS-Edge36        LOVE-AB12
            └─┬─┘└┬┘└┬─┘     └─┬─┘ └┬─┘└┬┘     └──┬─┘ └┬┘└┬┘
              │  │   └────────  │   │  └────────  │    │  └─ firmware hint
              │  └ model code   │   └ model code  │    └ model code
              └ literal prefix  └ literal prefix  └ literal prefix
```

The dual-signal requirement matters because the **Gen-2 service UUID
is the standard Nordic UART Service** (`6E400001-B5A3-F393-E0A9-E50E24DCCA9E`),
which is shared with many unrelated hobby projects and our own
`IoTV*` device family. The local-name corroboration prevents
mis-attribution.

## Protocol Generations

| Generation | Service UUID(s) | Notes |
|------------|-----------------|-------|
| 1 (legacy) | `0000FFF0-0000-1000-8000-00805F9B34FB` | Earliest hardware; generic 0xFFF0 UUID |
| 2          | `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Standard Nordic UART Service (NUS) |
| 3          | `XY300001-002Z-4BD4-BBD5-A6920E4C5653` | Variable XY / Z (32 possible UUIDs) per buttplug.io spec |

For Gen-3, observed in our 2026 capture: `4A300001-0023-4BD4-BBD5-A6920E4C5653`
(X=4, Y=A, Z=3). The parser checks the stable middle/suffix bytes
(`30000` … `-4BD4-BBD5-A6920E4C5653`) so any of the 32 listed
variations matches.

## Metadata Exposed

| Key | Example | Notes |
|-----|---------|-------|
| `model_code` | `J`, `Edge`, `Lush`, `Domi` | Letter(s) between the prefix and the firmware digits |
| `firmware_hint` | `0123`, `36`, `12` | Trailing digits in the local name (raw) |
| `firmware_version` | `23`, `36`, `12` | Last 2 digits of `firmware_hint`, per buttplug.io's "the last 2 numbers denote the firmware version" rule |
| `model_subcode` | `01` (only set when present) | Any digits between the letter(s) and the 2-digit firmware version; meaning not documented in the public spec |
| `product_name` | `Solace`, `Domi`, `Edge`, `Lovense Edge`, `Lovense (model letter J)` | Resolved product name. Single-letter codes use the published mapping; multi-letter codes are used verbatim; unknown single letters are flagged |
| `product_name_note` | `letter not in public buttplug.io spec — possibly a post-2024 SKU` | Set only when the single-letter model code is unmapped |
| `protocol_generation` | `1` / `2` / `3` | Which UUID family triggered the match |
| `device_class` | `personal_wellness` | adwatch classification |

### Single-letter model-code mapping (per buttplug.io)

| Letter | Product |
|--------|---------|
| A | Nora |
| B | Max |
| C | Nora |
| H | Solace |
| L | Ambi |
| O | Osci |
| P | Edge |
| S | Lush |
| W | Domi |
| Z | Hush |

Letters not in this table (e.g. `J` in `LVS-J0123`) are intentionally
NOT guessed — the public reverse-engineering spec at
[buttplug.io](https://buttplug.io/stpihkal/protocols/lovense/) does
not list them, and Lovense has been observed reusing letters across
hardware revisions (compare A=Nora and C=Nora). Newer SKUs released
since the spec was last updated (Solace Pro, Gravity, Lapis, Calor,
Diamo, Flexer, etc.) may use additional letters; if you can match a
letter to a product by direct observation, please update the table.

## Identity Hashing

```
identifier_hash = SHA256("lovense:{local_name}")[:16]
```

The local name carries enough identity for stable grouping across BLE
MAC rotation (Lovense devices rotate their MAC every few minutes).
Two physical devices of the same model with the same firmware hint
will hash to the same identity — this is an inherent limit of the
advertisement payload; the per-unit identifier lives behind a
connected GATT session.

## Captured Devices (2026 export)

| local_name | device_id | sightings | RSSI max | UUID |
|------------|-----------|-----------|----------|------|
| `LVS-J0123` | `BC99072D-…-2D28ED304536` | 835 | −70 dBm | `4A300001-0023-4BD4-BBD5-A6920E4C5653` |
| `LVS-J0123` | (same device) | 17 | −77 dBm | *(none — secondary advert)* |

The single physical device emits two distinct advertisement
signatures: a primary broadcast that includes the Gen-3 service UUID
(835 sightings, stronger RSSI) and a secondary slimmer broadcast
that drops the UUID (17 sightings, weaker RSSI). adwatch records
both signatures; the parser attributes both to the same
`identifier_hash` because the local name carries enough identity.

Decoded from `LVS-J0123`:

```
model_code         = J
firmware_hint      = 0123
firmware_version   = 23
model_subcode      = 01
product_name       = Lovense (model letter J)
product_name_note  = letter not in public buttplug.io spec — possibly a post-2024 SKU
protocol_generation = 3
```

## What We Cannot Parse Without GATT

- Per-unit serial number / device-type string
- Battery level (exposed via GATT 0x180F on most generations)
- Motor speed / pattern state (proprietary GATT characteristics)
- Live control surface — opening or controlling the device is out of
  scope for adwatch's passive scanner.

## Privacy Considerations

Lovense devices are intimate hardware. The presence of `LVS-` /
`LOVE-` names in a BLE scan reveals personal device ownership.
adwatch reports the attribution because that is what the
advertisement carries — the privacy concern is upstream (a device
that broadcasts its brand identifier in plaintext). The reverse-
engineered Lovense protocol is public knowledge and Lovense itself
publishes its naming convention to third-party integrations, so
attribution does not require any private reverse-engineering on
adwatch's part.

## References

- buttplug.io Lovense spec: https://buttplug.io/stpihkal/protocols/lovense/
- Original `stpihkal` reverse-engineering notes: https://metafetish.gitbooks.io/stpihkal/hardware/lovense.html
- buttplug.io project: https://buttplug.io/
