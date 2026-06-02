# Unknown BLE Family — Suspected Hatch Rest 2nd Gen / Rest+ 2nd Gen ("RIoT")

## Overview

A persistent BLE emitter advertising **only** the 128-bit service UUID
`D30F3C56-8170-5B99-A9E9-A849A69E8407` — no local name, no manufacturer
data, no service data. The strong working hypothesis is that this is a
**Hatch Rest 2nd Generation** or **Hatch Rest+ 2nd Generation** sound
machine. Hatch's internal platform name for this product line is
**"RIoT"** (Rest IoT); the open-source `hatch_rest_api` Python library
uses product codes `riot` (Rest 2 / HBR4400) and `riotPlus` (Rest+ 2 /
HBR4600), both routed through the same `RestIot` class.

The parser ships as `vendor: Unknown` with `suspected_product`
information at **medium confidence** — pending a 2-minute scan-response
or GATT-connect verification.

## Why we think this is a Rest 2 / Rest+ 2

| Signal | Evidence | Confidence |
|--------|----------|------------|
| ESP32-shaped advertisement | A single 128-bit service UUID with no `name` and no `mfr` is the canonical ESP32 BLE-adv pattern — a 128-bit UUID alone consumes 18 of the 31 legacy adv-payload bytes, so Espressif firmware commonly drops the local name into the scan response rather than the primary advertisement. | High |
| Rest 2 / Rest+ 2 use Espressif ESP32 | FCC teardown photos for `2AFYZ-HBREST2` (Rest 2) and `2AFYZ-HBRESTPLUS2` (Rest+ 2), both filed Aug 2021, show **ESP32-WROVER-E** modules with ESP32-D0WD silicon. The Nordic chipset from the 1st-gen Rest was dropped. | High |
| No public BLE reversing exists | Every open-source Hatch integration controls the 2nd-gen Rest via **AWS IoT MQTT only** (cloud). The Rest 2 / Rest+ 2 BLE GATT has never been publicly reverse-engineered — which neatly explains why this UUID returns *zero* hits anywhere on the web. | High |
| Field-capture behaviour matches | 8,388 sightings of this UUID across 4 separate exports at RSSI ~-67 dBm — an always-on emitter in a fixed home location, exactly how a bedside Rest 2 / Rest+ 2 behaves while idle on its WiFi connection. | Medium |
| Distinct from the 1st-gen Rest | Older Hatch Rest broadcasts manufacturer data with CID `0x0434` and a "<Room> Hatch" local name (the "RTj" protocol decoded by `HatchParser`). The 2nd-gen line moved to a completely different chipset and presumably a redesigned BLE service. | High |

What we **can't** confirm without ground truth:

- That this UUID belongs to *any* particular Hatch SKU. The same adv
  shape would be emitted by any nearby ESP32-based home device that
  advertises a single vanity UUID. Alternative candidates include
  smart bulbs, mesh nodes, scales, or other small custom IoT builds.
- That the same UUID is used by both Rest 2 and Rest+ 2 (rather than
  different vanity UUIDs per SKU).

## How to verify (under 2 minutes)

In priority order — each step strengthens the identification:

1. **MAC OUI lookup (free, instant).** Find the device in a BLE scanner
   that exposes the public-side MAC (e.g. nRF Connect on Android — iOS
   hides MACs). The OUI should resolve to **Espressif Inc.** Common
   Espressif OUIs include `24:0A:C4`, `30:AE:A4`, `7C:9E:BD`,
   `C4:DD:57`, `E0:E2:E6`. If the OUI is anything else (Nordic,
   Realtek, Murata), it's not a 2nd-gen Hatch.
2. **Active scan (free, ~30 sec).** Switch the scanner to active
   scanning. Many ESP32 firmwares put the local name in the **scan
   response** (returned only on active scan), not the primary
   advertisement. Hatch-…, rest-…, or similar in the scan response is
   a strong positive.
3. **GATT connect (free, ~3 min).** Connect to the device in nRF
   Connect. Read the **Device Information Service** (0x180A)
   characteristics — `Manufacturer Name`, `Model Number`, `Firmware
   Revision`. A "Hatch", "Hatch Baby", or "Rest" string is definitive.
4. **Toggle test (free, ~2 min).** Power-cycle the suspected Rest
   device while watching the scan. The `d30f3c56-…` UUID should drop
   from the scan within a few seconds and return when the device
   re-boots.

If any of these confirm, the parser metadata should be upgraded:
`suspected_confidence` → `high`, the parser renamed to
`HatchRest2Parser`, and the doc moved to `hatch-rest-2.md`.

## Advertisement Structure

| Field | Source | Notes |
|-------|--------|-------|
| Service UUID | `D30F3C56-8170-5B99-A9E9-A849A69E8407` | the family anchor (primary advertisement) |
| Local name | (absent from primary advertisement) | ESP32 31-byte budget consumed by the 128-bit UUID; check the **scan response** with active scanning |
| Manufacturer data | (absent) | same reason |
| Service data | (absent) | same reason |

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Presence | service UUID + RSSI | "device is nearby and on" |
| Suspected product | hard-coded hypothesis | `Hatch Rest 2nd Gen / Rest+ 2nd Gen (RIoT)` |
| Suspected product codes | hard-coded hypothesis | `riot`, `riotPlus` |
| Suspected chipset | hard-coded hypothesis | `Espressif ESP32-WROVER-E` |
| Adv shape | hard-coded | `esp32_128bit_uuid_only` — useful diagnostic when grouping similar emitters |

## What We Cannot Parse

- Vendor / product confirmation (until verification).
- Sub-model disambiguation — Rest 2 vs Rest+ 2 (they may share the UUID).
- Any state (on / off, sound program, volume, scene, alarm armed,
  brightness) — all of that lives behind the AWS-IoT cloud control
  path on the 2nd-gen Rest line; BLE is used solely for provisioning
  and possibly OTA.
- Firmware version, hardware revision.

## Stable Identity

The advertisement has no embedded per-unit signal beyond the BLE MAC,
so identity is anchored on the MAC —
`stable_key = unknown_d30f3c56:<mac>`. If the user's iOS scanner is
already bonded to the device, the CoreBluetooth peripheral identifier
will remain stable across MAC rotations and the parser will still see
one logical device.

## References

- `dahlb/hatch_rest_api` — product codes `riot` (Rest 2) and
  `riotPlus` (Rest+ 2) → `RestIot` class (cloud-only) —
  <https://github.com/dahlb/hatch_rest_api>
- `dahlb/ha_hatch` discussion #16 — Rest+ 2nd Gen support is
  cloud-only —
  <https://github.com/dahlb/ha_hatch/discussions/16>
- FCC ID `2AFYZ-HBREST2` — Hatch Rest 2nd Gen, ESP32-WROVER-E
  confirmed —
  <https://fccid.io/2AFYZ-HBREST2>
- FCC ID `2AFYZ-HBRESTPLUS2` — Hatch Rest+ 2nd Gen, ESP32-WROVER-E
  confirmed —
  <https://fccid.io/2AFYZ-HBRESTPLUS2>
- ESP-IDF advertising-data 31-byte length constraint —
  <https://github.com/espressif/esp-idf/issues/2443>
- Hatch Baby FCC grantee index (`2AFYZ`) —
  <https://fccid.io/2AFYZ>
- Older Hatch Rest 1st-gen BLE protocol (for contrast — different
  chipset, different adv shape) —
  <https://github.com/kjoconnor/pyhatchbabyrest>
- Companion vendor-unconfirmable fingerprint parsers:
  - `Unknown3E1D50CDParser`
  - `Unknown65333333Parser`
  - `Unknown3DD2VanityCIDParser`
