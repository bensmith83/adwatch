# Samsung FD69 Find Network Plugin

## Overview

**Service UUID `0xFD69`** is officially assigned to **Samsung Electronics Co., Ltd.** in the Bluetooth SIG's 16-bit member UUID registry. It is the canonical service UUID for Samsung's **Find Network** / **SmartThings Find** / **Offline Finding (OF)** protocol — the crowd-sourced location-tracking system that Galaxy phones, watches, tablets, earbuds, and Galaxy SmartTags use to locate each other when they are out of network range.

The protocol has two complementary roles, both of which appear on `FD69`:

- **Lost devices broadcast on `FD69`.** When a registered device (phone, watch, tablet, or a SmartTag whose owning phone is offline) enters lost / offline-finding mode, it advertises a rotating-pseudonym BLE frame under service UUID `FD69`. The frame is the bait that helper devices look for.
- **Online Galaxy devices scan for `FD69`.** Per Yu et al.'s "Privacy Analysis of Samsung's Crowd-Sourced Bluetooth Location Tracking System" (USENIX Security '23), online Samsung phones / tablets continuously scan with a filter on the `FD69` service UUID. When they spot one, they encrypt the sighting (BLE address + RSSI + GPS location) and relay it to Samsung's backend, which forwards it to the lost device's owner.

So `FD69` carries two kinds of traffic: "I am lost — please relay my pseudonym" and (less commonly observable on the wire as service data, but encoded in the radio behaviour) "I am scanning on behalf of the network." In `research/adwatch_export 9.json` we observed nine anonymous `FD69` service-data frames — no local name, no manufacturer data — which the existing `GalaxyWatchParser` could not handle because it requires the local name to start with `"Galaxy Watch"`. This plugin is the catch-all for those anonymous frames.

`SmartTagParser` handles a **different** service UUID (`0xFD5A`), which is the dedicated SmartTag setup / unprovisioned advertise service. `FD69` is the wider Find-Network service shared across the whole Galaxy ecosystem.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (16-bit) | `0xFD69` — SIG-assigned to **Samsung Electronics Co., Ltd.** |
| Service data | Present, ≥ 10 bytes, first byte ∈ {0x00, 0x03, 0x10} |
| Manufacturer data | Typically absent in anonymous mode |
| Local name | Absent (if present and starts with `"Galaxy Watch"`, dispatch falls back to `GalaxyWatchParser`) |
| BD_ADDR | Random / resolvable, rotates frequently |

### Three Observed Frame-Type Variants

The first byte of the `FD69` service data is a frame-type tag. We observed three values in the field; the parser rejects any other value to avoid false positives from unrelated `FD69` traffic.

| Frame byte | Total length | Working name | Trailer pattern | Likely role |
|---|---|---|---|---|
| `0x00` | 15 B | Anonymous finder / neighbor-discovery | trailer ends in `40 80` | Galaxy phone/watch broadcasting "finder available" while scanning for nearby SmartTags |
| `0x03` | 14 B | Paired-mode tag/device advertise | trailer is a single `01` | A paired Galaxy device or tag advertising its per-rotation pseudonym |
| `0x10` | 20 B | Galaxy Network relay payload | trailer is a 5-byte tail (e.g. `1e 2b 0e d4 ff`) | Longer encrypted offline-finding payload |

Each frame decomposes into:

```
byte 0         : frame-type tag        ∈ {0x00, 0x03, 0x10}
bytes 1..9     : per-device anchor     (9 bytes, stable across captures of same device)
bytes 10..end  : trailer / encrypted   (length varies by frame type)
```

Concrete captures from `research/adwatch_export 9.json`:

```
0x00 :  00 0fe648c99c03681e00 44a7b6 40 80
0x03 :  03 b8a647dcacc74956e0 58043f 01
0x10 :  10 81c7acc361ff9908be 66e3ae5200 1e2b0ed4ff
```

The frame-type names (`finder`, `paired-mode`, `Galaxy Network`) are working hypotheses derived from byte-count + trailer pattern; the public arxiv 2210.14702 analysis focuses on the rotating-pseudonym encryption rather than on the exact byte-level frame partition, so we deliberately label the parser metadata with the raw byte (`0x00` / `0x03` / `0x10`) rather than these hypothesized names.

## Stable Key

`samsung_fd69:<device_anchor_hex>` where `device_anchor_hex` is the 9-byte region immediately after the frame-type byte.

Rationale:

- **MAC is useless.** Per Yu et al., the BD_ADDR rotates on roughly the same cadence as the offline-finding pseudonym (every ~15 minutes / hourly depending on Samsung's tuning). Keying on MAC would fragment a single physical device into dozens of identities per hour.
- **The 9-byte anchor was identical** across the two `0x03` sightings of `b8 a6 47 dc ac c7 49 56 e0 …` in `adwatch_export 9.json`, taken seconds apart from the same household. That makes it the natural per-device anchor for at least a single rotation window.
- **This is a rotation-window identity, not a long-term identity.** The whole point of Samsung's design is that the anchor itself rotates every ~15–60 minutes. Two sightings of the same physical device hours apart will produce different `device_anchor_hex` values. Long-term re-identification requires the encryption key, which only the owning Samsung account possesses.

## Detection Significance

- **Samsung household density indicator.** A scan that turns up multiple distinct `samsung_fd69` anchors is strong evidence of multiple Galaxy phones / watches / tablets in radio range. Conversely a scan with zero `FD69` traffic in a populated area is mildly anomalous (or simply Apple-dominant).
- **"Galaxy ecosystem present" signal.** Useful for inferring the brand mix of a location without needing model-specific fingerprints.
- **Lost-device proxy.** A `0x03` or `0x10` frame from an otherwise quiet device is a hint that *something* nearby is in offline-finding broadcast mode — could be a tag whose phone is dead, a phone that's been left behind, or a watch that has lost its owner.
- **Pairs well with `GalaxyWatchParser` and `SmartTagParser`.** Anonymous `FD69` frames are precisely the ones those parsers ignore; this plugin closes the gap.

## What We Cannot Parse from `FD69`

- **The rotating-pseudonym payload.** Bytes 10..end of each frame are derived (per the arxiv paper) from an AES / HKDF chain seeded by a key that only Samsung's servers and the device's owner possess. The on-wire bytes are deliberately indistinguishable from random.
- **Long-term device identity.** See "Stable Key" — anchor rotates by design.
- **Device class.** A `0x03` or `0x10` frame does not on its face tell us whether the emitter is a phone, a watch, a tablet, or a Galaxy SmartTag. We default `device_class` to `"phone"` because Galaxy phones are the dominant emitter of anonymous `FD69` finder broadcasts (they continually announce finder availability), but the metadata field `device_class_note` is explicit about the uncertainty.
- **Battery / sensor telemetry.** None — this is purely a finder / lost-device protocol.

## References

- [Yu et al., "Privacy Analysis of Samsung's Crowd-Sourced Bluetooth Location Tracking System" (arxiv 2210.14702, USENIX Security '23)](https://arxiv.org/abs/2210.14702) — the canonical academic analysis of the Samsung Offline Finding protocol. Confirms `FD69` as the OF service UUID, documents lost-device broadcast cadence, helper-device scan filter, AES-based pseudonym chain, and overall privacy properties.
  - [HTML mirror (ar5iv)](https://ar5iv.labs.arxiv.org/html/2210.14702)
  - [USENIX pre-publication PDF](https://www.usenix.org/system/files/sec23winter-prepub-498-yu.pdf)
- [Bluetooth SIG Assigned Numbers — 16-bit Member UUIDs (YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — confirms `0xFD69` is assigned to "Samsung Electronics Co., Ltd."
- `research/adwatch_export 9.json` (this repo) — nine anonymous `FD69` captures that motivated this plugin, including the double-capture of `03 b8 a6 47 dc ac c7 49 56 e0 …` that justifies the 9-byte device-anchor stable key.
- Sibling parsers: `Sources/Parsers/GalaxyWatchParser.swift` (named-watch dispatch path), `Sources/Parsers/SmartTagParser.swift` (`FD5A`, the SmartTag-specific service), `Sources/Parsers/SamsungGalaxyBudsParser.swift` (also touches `FD69` for buds setup).
