# Philips Hue / Signify BLE Protocol

## Overview

Signify Netherlands B.V. (formerly Philips Lighting B.V.) ships smart lighting under the **Philips Hue** brand: bridges, bulbs, plugs, light strips, and the newer Hue Secure camera line. Hue devices fall back to BLE when out of reach of a Zigbee/Hue Bridge, and the Hue Bridge itself emits a BLE beacon in pairing/commissioning mode.

All Hue BLE traffic surfaces under the Bluetooth SIG 16-bit member UUID **`0xFE0F`**, registered to Signify.

## Identifiers

- **Service UUID:** `FE0F` (16-bit, SIG-allocated to Signify Netherlands B.V.)
- **Local name pattern:** user-assigned room/zone label, often with a trailing space (e.g. `"Sala "`, `"Entrance "`, `"Living Room "`)
- **Device class:** `lighting`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FE0F` (full: `0000fe0f-0000-1000-8000-00805f9b34fb`) | Signify SIG assignment |
| Service data key | `FE0F` | Mirrors the service UUID |
| Local name | `<room label>` (optional, trailing space) | App-assigned, cleared once the unit is fully provisioned |

### Service-data body

5-byte frame observed across four distinct units in three buildings:

```
02 10 FF FF 02
│  │  └─┬─┘ └── mode byte (0x02 = controllable)
│  │    └───── reserved / placeholder
│  └────────── ad type / state (0x10 = commissioned-idle)
└───────────── frame version (0x02)
```

Byte map:

| Offset | Field | Value | Notes |
|--------|-------|-------|-------|
| 0 | `frame_version` | `0x02` | All captured frames |
| 1 | `state_byte` | `0x10` | Commissioned / idle |
| 2-3 | reserved | `0xFFFF` | Placeholder |
| 4 | `mode_byte` | `0x02` | Controllable from Hue app |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or service_data[FE0F] | Hue device nearby |
| Frame version | service_data[FE0F][0] | Currently `0x02` |
| Operating state | service_data[FE0F][1] | `0x10` = commissioned/idle |
| Mode | service_data[FE0F][4] | `0x02` = controllable |
| Room name | local_name | User-assigned; trailing space trimmed |
| Vendor | constant | `Signify` |

### What We Cannot Parse (requires GATT or Hue Bridge)

- Bulb on/off state
- Brightness / colour temperature / hue / saturation
- Current scene
- Firmware version
- Zigbee mesh topology / paired devices
- Account / Hue cloud identifiers
- Hue Secure camera media

## Sample Advertisements

```
"Sala " — 6 sightings
  Service UUID: FE0F
  Service data: { "FE0F": "0210ffff02" }
  Manufacturer data: (none)
```

```
"Entrance " — 5 sightings
  Service UUID: FE0F
  Service data: { "FE0F": "0210ffff02" }
  Manufacturer data: (none)
```

```
(no local name) — 2 sightings
  Service UUID: FE0F
  Service data: { "FE0F": "0210ffff02" }
```

All four captured units share the same 5-byte service-data body — the frame is uniform across firmware revisions and product variants.

## Identity Hashing

```
identifier = SHA256("philips_hue:{mac}")[:16]
```

Hue devices do not rotate their MAC frequently (the BLE radio is on the same SoC as the Zigbee radio, which has a stable factory MAC), so MAC-based hashing produces a stable presence identifier.

## Detection Significance

- Indicates a Signify-branded lighting fixture or Hue Bridge in commissioning mode
- Always-on BLE for Hue Sync, Hue Bluetooth, and Bridge pairing
- Room labels can leak interior structure ("Bedroom", "Bathroom", "Kids") — useful for location fingerprinting

## Parsing Strategy

1. Match on service UUID `FE0F` OR `serviceData[FE0F]`
2. If service-data present, decode `frame_version`, `state_byte`, `mode_byte` from the 5-byte body
3. Trim trailing whitespace from `local_name` and surface as `room_name`
4. Return device class `lighting` with `vendor=Signify`

## References

- [Signify](https://www.signify.com/) — manufacturer (Philips Hue parent company)
- [Bluetooth SIG 16-bit UUID list — member UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFE0F → Signify Netherlands B.V. (formerly Philips Lighting B.V.)`
- Observed in `research/adwatch_export 12.json` — four distinct units, three buildings, identical body
