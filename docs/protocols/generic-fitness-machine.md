# Generic Fitness Machine (SIG-Profile)

## Overview

A *categorical* parser that fires on any of the Bluetooth SIG-standardised
fitness-profile service UUIDs and classifies the device as fitness
equipment without attempting to attribute the OEM. Pair with a per-vendor
parser (Garmin, Polar, Stryd, Concept2PM5, COROSWatch, Whoop, etc.) when
one can be written — both fire alongside and the merged record carries
attribution from the vendor parser plus the category tag from this one.

The parser exists because a meaningful slice of captured fitness
equipment is shipped under unbranded Chinese ODM labels (WUQI-microchip-
based bikes, generic foot pods, off-brand treadmills) where the
advertisement carries no manufacturer data, no service data, no vendor-
specific UUID — only the SIG profile UUID and a serial-style localName.
Attempting to identify the OEM from a name like `WQ-88X102810034`
without further capture is unreliable, but classifying the device as a
cycle/treadmill/power-meter category is still actionable.

## Identification

| Signal | Value | Meaning |
|--------|-------|---------|
| Service UUID `0x1816` | Cycling Speed and Cadence (CSC) | Bikes, some treadmills |
| Service UUID `0x1818` | Cycling Power | Power meters, smart trainers |
| Service UUID `0x1814` | Running Speed and Cadence (RSC) | Foot pods, treadmills |
| Service UUID `0x1826` | Fitness Machine Service (FTMS) | Modern treadmills, bikes, ellipticals, rowers |

The parser surfaces the matched SIG profile in
`metadata.service_profile` and `metadata.attribution_method =
"sig_profile_uuid"`. `metadata.vendor_attribution = "unknown"` is always
present so downstream consumers can distinguish heuristic categorisation
from real vendor attribution.

## Local-Name Decoding

When the localName follows the canonical "industrial OEM" pattern
`<2–5 letter brand>[-]<alphanumeric model ending in letter><4–12 digit
serial>`, the parser decomposes it into:

```
WQ-88X102810034
└┬┘  └┬┘└────┬───┘
brand model  serial
```

| Localname           | brand_prefix | model_code | serial      |
|---------------------|--------------|------------|-------------|
| `WQ-88X102810034`   | `WQ`         | `88X`      | `102810034` |
| `TM-A20012345678`   | `TM`         | `A20`      | `012345678` |
| `Treadmill-1234`    | (none — fails strict pattern) | — | — |

### Known WUQI-Chipset OEM Brand Prefixes

The `WUQI Microelectronics` BL602/WQ7xxx/WQ9xxx-class chips ship in
many unbranded fitness sensors. Vendors that don't customize the SDK
default name leak the chipset family in the prefix. Confirmed in the
wild:

| Prefix | Notes |
|--------|-------|
| `WQ-`  | Most common — generic CSC bike sensors, no other branding. Captured 516 sightings × 4 exports on `WQ-88X102810034`. |
| `TM-`  | Treadmill-class devices on the same SoC family. |

Add new prefixes here only after a recurring cross-export capture is
verified and the WUQI chipset attribution is confirmed via either FCC
filing, GATT 0x180A Device Information read, or vendor doc match.

Names that don't match the strict pattern are surfaced verbatim as
`metadata.local_name` only.

## Wire Format

Presence-only — the advertisement carries no telemetry. Live
speed/cadence/power/heart-rate flow over GATT on the corresponding
characteristics:

| Service | Live characteristics |
|---------|----------------------|
| CSC `0x1816`     | `CSC Measurement 0x2A5B`, `CSC Feature 0x2A5C`, `Sensor Location 0x2A5D` |
| Cycling Power `0x1818` | `Cycling Power Measurement 0x2A63`, `Feature 0x2A65`, `Sensor Location 0x2A5D` |
| RSC `0x1814`     | `RSC Measurement 0x2A53`, `RSC Feature 0x2A54` |
| FTMS `0x1826`    | many — `Treadmill Data 0x2ACD`, `Indoor Bike Data 0x2AD2`, `Rower Data 0x2AD1`, etc. |

## Identity Hashing

```
identifier_hash = SHA256("generic_fitness_machine:serial:<brand>:<model>:<serial>")[:16]   # when name splits cleanly
identifier_hash = SHA256("generic_fitness_machine:mac:<MAC>")[:16]                          # fallback
```

The brand/model/serial breakdown is the stable per-unit identity when
available — it survives BLE MAC rotation. Bare-UUID broadcasts (no
localName) fall back to the rotating BD_ADDR.

## What We Cannot Parse Without GATT or Vendor Attribution

- Specific OEM / SKU
- Live cadence, speed, power, distance, calories, incline, resistance
- Heart-rate (a separate SIG service)
- Firmware version

## What Pinning a Specific OEM Would Need

If a "generic" record recurs and you want to upgrade it to a named
vendor parser:

1. **GATT enumeration** — connect once and list primary services.
   Custom 128-bit vendor service UUIDs usually encode the OEM in the
   high bytes.
2. **Device Information Service (`0x180A`)** read — characteristics
   `Manufacturer Name 0x2A29`, `Model Number 0x2A24`,
   `Hardware Revision 0x2A27`, `Firmware Revision 0x2A26`.
3. **GAP Appearance (`0x2A01`)** — `0x0480` = cycling, `0x0500` =
   treadmill, etc.

Any one of those usually pins the SKU.

## References

- [Bluetooth SIG — Cycling Speed and Cadence Service 1.0](https://www.bluetooth.com/specifications/specs/cycling-speed-and-cadence-service-1-0/)
- [Bluetooth SIG — Fitness Machine Service 1.0](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/)
- [Bluetooth SIG — Running Speed and Cadence Service 1.0](https://www.bluetooth.com/specifications/specs/running-speed-and-cadence-service-1-0/)
- [Bluetooth SIG — Cycling Power Service 1.0](https://www.bluetooth.com/specifications/specs/cycling-power-service-1-0/)
- Captured device `WQ-88X102810034` in `research/adwatch_export 14.json`
  (129 sightings, 1 device, CSC profile only).
