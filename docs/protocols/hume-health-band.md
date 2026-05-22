# Hume Health Band Plugin

## Overview

The **Hume Health Band** (model `2208`) is a screen-free wristband from [Hume Health](https://humehealth.com/) targeting the longevity / metabolic-health market — explicitly positioned as a subscription-free alternative to Whoop. The hardware ships 5 LEDs + 4 photodiodes for HR, HRV, SpO₂, skin temperature, sleep staging, and a metabolic score. IP68, BLE 5.0, ~4–7 day battery, 8.6 g.

This is a different company from **Hume AI** (the voice-emotion-analysis API vendor). The wristband is OEM'd by a Shenzhen contract manufacturer — no FCC filing under "Hume Health" is publicly indexed.

The band advertises continuously over BLE behind unregistered pseudo-company-ID `0xF7F8` (well above the SIG-assigned `0x10C7` ceiling — Hume Health has not registered for SIG membership) plus the standard `0x180D` Heart Rate service. The inner sensor payload is opaque (no public decoder), but the device family and per-unit MAC suffix are recoverable from the advertisement.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Pseudo company ID | `0xF7F8` (**unregistered** with SIG — vendor magic, not assigned) |
| Service UUIDs | `0x180D` (Heart Rate, standard) |
| Local name | `Hume Band <MAC suffix>` (e.g. `"Hume Band B21F"`) — optional; the band sometimes advertises without a name |

### Manufacturer Data Layout (~29 bytes — real captures range 28–29)

```
Bytes 0..1   : f8 f7                   ← LE pseudo-company-ID
Bytes 2..7   : 22 08 04 02 02 07       ← 6-byte SDK / firmware signature,
                                          byte-identical across every B21F
                                          capture in research/adwatch_export 9.json.
                                          Surfaced as `frame_signature_hex`.
Bytes 8..9   : b2 1f                   ← 2-byte model ID in wire order;
                                          rendered "B21F" — matches the suffix
                                          in the local name `Hume Band B21F`.
                                          Surfaced as `model_id` (also kept as
                                          `mac_suffix` for backward compatibility).
Bytes 10..28 : opaque sensor TLV       ← variable across captures (rolling
                                          counters / sensor samples / battery,
                                          presumably). Surfaced verbatim as
                                          `payload_hex` (and the legacy
                                          `sensor_payload_hex` alias). No
                                          public decoder yet.
```

The fixed 8-byte signature (`f8 f7 22 08 04 02 02 07`) plus the trailing `b2 1f` model-tag is what we anchor on. The 0x180D Heart Rate service UUID is co-broadcast in the advertisement (CoreBluetooth surfaces it as `"180D"`). The variable region likely carries some mix of HR, battery, step count, or a wear-time counter — a controlled-experiment capture (band on a wearer with the Hume app open) would let us correlate.

### Stable Key

We use `hume_health_band:<MAC suffix>` so MAC rotations on the underlying random BD_ADDR collapse to a single band.

## Detection Significance

- **One device per home.** Hume Bands are personal wearables — a band sighting in a residential scan is informative for occupancy / wearer presence.
- **No app subscription required.** Unlike Whoop, the Hume Band stays advertising even if the user has stopped using the companion app, so abandoned units in drawers will still ping.

## What We Cannot Parse from Advertisements

- Live HR / HRV / SpO₂ / skin temp / sleep stage — likely encoded in the variable TLV but not yet decoded. Live values are reliable only via GATT through the Hume Health app.
- Battery — not surfaced in the advertisement.
- Metabolic score — proprietary algorithm running app-side.

## References

- [Hume Health Band product page](https://humehealth.com/pages/hume-band)
- [Hume Band Quickstart](https://humehealth.com/pages/humeband-quickstart)
- [Hume Band v2 page](https://humehealth.com/pages/hume-bandv2)
- [Robb Sutton — Hume Band review](https://robbsutton.com/hume-band-review/) — independent confirmation of model, advertising behaviour, app pairing flow.
- [Cybernews — Humeband review](https://cybernews.com/health-tech/humeband-review/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0xF7F8` is not assigned.
