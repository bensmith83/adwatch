# eBest IOT Inc. — BLE Asset-Tracking Beacon (CID `0x0437`)

## Overview

**eBest IOT Inc.** (Bluetooth SIG company identifier **0x0437**) makes BLE
"smart beacons" built to retrofit into **coolers / refrigerators** for asset
tracking — multi-year primary battery, advertise-only operation, no pairing.

The hardware is built on an **nRF52 module from Insigma Inc**, which is the
legal/FCC entity behind eBest IOT — the two are the same operation:

- **Insigma Inc** holds the IEEE MA-L OUI **`48:E6:95`** (Ashburn, VA;
  registered 2018-09-09) and the FCC grant for the nRF52 BLE module
  (**FCC ID `2AKR8BTIN00`**), whose responsible-party contact is at
  `ebest-iot.com`.
- **eBest IOT Inc.** holds the Bluetooth SIG **CID `0x0437`**.

Because the module embeds its own MAC (Insigma OUI) into the advertisement,
the device is attributable with high confidence even though the on-air BLE
address is random.

## BLE Advertisement Format

### Manufacturer Data (CID-first layout)

Real capture (`nearsight_export 6`, 1–2 devices, ~14 sightings):

```
37 04 | 48 E6 95 1C 4F B0 | 3D 0B 32 00 A8 FD 00 80 24 06 8F 00 61 00 43 42
 CID  |   device MAC      |        16-byte undocumented telemetry tail
```

| Bytes | Value | Meaning |
|-------|-------|---------|
| `[0..1]` | `37 04` | CID `0x0437` LE = **eBest IOT Inc.** — gate |
| `[2..4]` | `48 E6 95` | Insigma OUI — gate (defense in depth) |
| `[2..7]` | `48 E6 95 xx xx xx` | device MAC / serial — **stable identifier** |
| `[8..23]` | 16 bytes | undocumented vendor telemetry / state — **kept raw** |

### Other Signals

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `9E83` | vendor-proprietary 16-bit tag; **not** SIG-allocated (outside the `0xFCxx–0xFExx` member ranges). Soft hint only — used as a fallback dispatch path, not gated on. |
| Local name | `NA` or absent | `"NA"` is a placeholder ("N/A"), not a real device token — never gated on. |
| Address type | `random` | the embedded MAC, not the BLE address, is the durable key. |

## Identification

- **Primary gate:** manufacturer-data CID `== 0x0437` **AND** the embedded
  Insigma OUI `48:E6:95` at bytes `[2..4]`. Requiring the OUI (not CID alone)
  confirms the documented payload shape and avoids over-claiming any future
  unrelated eBest-CID frame.
- **Fallback dispatch:** the proprietary `9E83` service tag also routes to
  this parser (in case a scan drops the manufacturer data), but the parser's
  own gate still requires the CID+OUI structure before claiming.
- **Device class:** `tracker`.

## What We Can Surface

| Field | Source | Notes |
|-------|--------|-------|
| `vendor` | hard-coded | `eBest IOT Inc.` |
| `company_id` | hard-coded | `0x0437` |
| `oui_owner` | hard-coded | `Insigma Inc` |
| `device_mac` | mfg `[2..7]` | colon-formatted 6-octet MAC |
| `product_class` | hard-coded | `cooler/refrigerator asset-tracking beacon` |
| `service_tag` | service UUID | `9e83` when advertised |
| `payload_tail` | mfg `[8..]` | raw hex of the undocumented telemetry tail |

## What We Cannot Surface (Deliberately Not Decoded)

The 16-byte tail after the MAC is **undocumented**. Plausible fields
(battery, temperature, counters, an ASCII `"CB"` region/hw tag at the end)
are visible but **unverified** — there is no public datasheet and no
ground-truth capture to validate a field map. We therefore surface the tail
**raw only** and never decode it as temperature/battery. Revisit only with a
labelled, ground-truth capture.

## Stable Identity

The embedded 6-byte MAC is the durable per-unit key — the on-air BLE address
is random and rotates, which is exactly why the firmware embeds the real MAC
in the payload:

```
stable_key = ebest_iot_beacon:<device_mac>
identifier = SHA256(stable_key)[:16]
```

## Detection Significance

- An eBest IOT cooler/refrigerator asset-tracking beacon is in range —
  commonly deployed in retail / beverage-cooler fleets to track equipment
  placement and presence.
- Multiple distinct MACs in the `48:E6:95` OUI = multiple distinct beacons,
  not one rotating device.

## References

- Bluetooth SIG company identifiers (`0x0437 → eBest IOT Inc.`) —
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- IEEE MA-L OUI `48:E6:95` → Insigma Inc —
  <https://standards-oui.ieee.org/oui/oui.txt>
- FCC ID `2AKR8BTIN00` — Insigma Inc nRF52 BLE module (responsible party at
  ebest-iot.com) — <https://fccid.io/2AKR8BTIN00>
- eBest IOT Smart Beacon product page —
  <https://www.visioniot.com/product-smart-beacon.php>
- Parser: `Sources/Parsers/EbestIOTBeaconParser.swift`
