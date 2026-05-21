# MELK-OA21 BLE LED Controller Plugin

## Overview

MELK-OA21 is a Bluetooth Low Energy LED-strip controller in the broader **ELK-BLEDOM / LED-BLE / duoCo-StripX** family of rebadged Chinese smart-light controllers. The specific specimen captured in `research/adwatch_export 8.json` (2026-05-21) advertised:

| Signal | Value |
|---|---|
| Local name | `MELK-OA21   14` (note three spaces — fixed-width-padded numeric suffix) |
| Manufacturer data | absent |
| Service data | absent |
| Service UUIDs | absent |
| Address type | random |
| Sightings in window | 1 (RSSI -99 dBm — at the edge of the scan range) |

The advertisement is name-only — every actionable signal (model, per-unit serial) lives in the local-name string.

## Vendor Attribution

This took a non-trivial amount of web research; documenting both the hits and the dead ends for future maintainers.

**Definitive attribution: ELK-BLEDOM protocol family.**

- The Home Assistant custom integration [`dave-code-ruiz/elkbledom`](https://github.com/dave-code-ruiz/elkbledom) supports "LED STRIP NAMED ELK-, MELK-, LEDBLE or XROCKER" — i.e. MELK is documented as part of the same protocol family as ELK-BLEDOM, controlled through the same GATT write characteristic stack.
- GitHub issue [dave-code-ruiz/elkbledom#90](https://github.com/dave-code-ruiz/elkbledom/issues/90) ("MELK-OA21 Info / General MELK Reverse Engineering") confirms MELK-OA21 is sold as an Amazon LED Strip (ASIN B0DDKKX3QY), controlled by the [duoCo StripX](https://play.google.com/store/apps/developer?id=Melk) Android app, and includes mode/scene mapping notes.
- The [`homebridge-melk-ble-light`](https://libraries.io/npm/homebridge-melk-ble-light) plugin (Luke Wines) names this family explicitly and uses GATT write characteristic `0000fff3-0000-1000-8000-00805f9b34fb` to drive on/off/hue/saturation/brightness. (That UUID is a connect-time signal — it does not appear in advertisements.)
- Bluetooth-name reports in the Apple Community thread [What is ELK-BLEDOM Bluetooth device?](https://discussions.apple.com/thread/252785506) corroborate that MELK-prefixed names are advertised by the same class of rebadged-OEM LED controllers.

**What we still don't know:**

- The OEM / silicon vendor behind the MELK brand. The chips are sold under dozens of Amazon brand names and the original manufacturer is not publicly named in any source we found. We surface `family = "ELK-BLEDOM"` in metadata but **do not invent a specific vendor**.
- Whether the trailing numeric suffix (`14`) is a true per-unit serial, a batch number, or a deployment label. We capture it as `serial_suffix` and let downstream consumers interpret.

**Dead-end queries (all 2026-05-20):**

- `"MELK-OA21" BLE` — surfaces the elkbledom integration but no independent vendor.
- `"MELK OA21" product` — same.
- `MELK printer / kiosk / pos / appliance` — no relevant hits; rules out the "Korean industrial equipment" hypothesis suggested by the `MELK` letters.
- `melk.co.kr` — no relevant vendor site.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `MELK-OA21<whitespace><digits>` |
| Manufacturer data | none (rejected if present — disjoint rule) |
| Service data | none (rejected if present — disjoint rule) |
| Service UUIDs | none (rejected if present — disjoint rule) |

### Local Name Format

```
MELK-OA21   14
└──┬──┘└┬┘└┬┘└┬┘
   │   │  │  └── trailing digits — `serial_suffix` (parser captures)
   │   │  └───── whitespace padding (1+ space/tab characters, fixed-width
   │   │         in observed sample but parser does not enforce width)
   │   └────── model code — captured as `model = "OA21"`
   └────────── family marker `MELK-`
```

The padding-then-digits layout is consistent with a manufacturing-line stamp where a fixed-width name field is right-aligned with a sequence number — common in OEM firmware where the broadcast name is generated from a serial register.

The parser scopes its stable key to `melk_device:<MODEL>:<SERIAL>`, anchoring on the in-name suffix rather than the BD_ADDR (which is random and rotates). Repeated sightings of the same physical controller across MAC-randomisation events therefore deduplicate cleanly.

## Detection Significance

- **Highly specific local-name pattern.** `MELK-OA21<ws>+<digits>$` is unlikely to collide with another vendor's advertisement.
- **Disjoint mfr/svc rule.** The MELK-OA21 advertisement is name-only; if manufacturer data, service data, or service UUIDs are present, it's not our device. This protects against false positives if some other device happens to broadcast a colliding name (extremely unlikely, but cheap to defend against).
- **Family-level grouping ready.** Surfacing `family = "ELK-BLEDOM"` lets downstream consumers count MELK-OA21 sightings alongside ELK-BLEDOM, LEDBLE and XROCKER variants once those siblings are added.

## What We Cannot Parse

- **Specific OEM vendor.** Documented above — sold under many brand names; not publicly disclosed.
- **Light state / colour / brightness.** All controllable state lives behind the GATT characteristic at connect time, not in the advertisement.
- **Firmware / hardware version.** Not advertised.

## Related Parsers

- `ELKBLEDOMParser` — handles `^ELK-BLEDOM` names. Same protocol family, different name prefix; routed separately by `Pipeline.swift`.

## References

- `research/adwatch_export 8.json` — captured MELK-OA21 device (entry at line 2479, local name `MELK-OA21   14`, sighting count 1, RSSI -99 dBm)
- [dave-code-ruiz/elkbledom](https://github.com/dave-code-ruiz/elkbledom) — Home Assistant integration documenting ELK-/MELK-/LEDBLE/XROCKER family
- [dave-code-ruiz/elkbledom#90 — MELK-OA21 Info / General MELK Reverse Engineering](https://github.com/dave-code-ruiz/elkbledom/issues/90)
- [homebridge-melk-ble-light on libraries.io](https://libraries.io/npm/homebridge-melk-ble-light)
- [Apple Community — What is ELK-BLEDOM Bluetooth device?](https://discussions.apple.com/thread/252785506)
- [home-assistant/core#121718 — ELK/MELK protocol BLE LED devices detection](https://github.com/home-assistant/core/issues/121718)
