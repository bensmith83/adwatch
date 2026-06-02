# Lester Smart Transformer (Landscape Lighting)

## Overview

Lester Electrical of Nebraska, Inc. is the **OEM** behind a Bluetooth-controlled
landscape-lighting transformer that ships under several retail brand skins.
The unit replaces a manual landscape-lighting transformer/timer and exposes
on/off, scheduling, and dimming over BLE. Pairing is done in the brand-
specific phone app, which prompts the user to "tap the serial number matching
the sticker on the transformer."

## Brand Skins

All three apps share Lester's Android package prefix
`com.lester.landscapetransformer.*` and the same BLE service UUID — they are
the same firmware under different paint:

| Brand | iOS App | Android Package |
|-------|---------|-----------------|
| Alliance Outdoor Lighting (iTimerPro / iTimerPro-2) | id1053543813 (Nov 2015) | `com.lester.landscapetransformer.alliance` |
| Constellation Pro | id1273815799 | `com.lester.landscapetransformer.constellationpro` |
| Tru-Scapes Smart Lighting (incl. Belgard) | id1331987368 | `com.lester.landscapetransformer.truscapes` |

The BLE advertisement does **not** identify the brand skin — that's printed
on the physical transformer sticker. The detector reports the OEM family and
leaves brand disambiguation to physical inspection.

## Manufacturer

**Lester Electrical of Nebraska, Inc.** — Lincoln, Nebraska. Best known for
industrial battery chargers; the Smart Transformer line is their consumer
landscape-lighting branch (<https://www.lesterelectrical.com/products/smart-transformers>).

## BLE Advertisement Structure

### Service UUIDs

| UUID | Description |
|------|-------------|
| `3A3E0EAE-EDBF-11E4-90EC-1681E6B88EC1` | Lester Smart Transformer proprietary control service |

The UUID is **UUIDv1 (time-based)** and the embedded timestamp resolves to
early 2015 — matching the Nov-2015 release of the original Alliance
Transformer app. It was almost certainly generated once by `uuidgen` on a
Lester developer workstation and baked into the firmware unchanged ever
since.

A companion GATT characteristic
`f36c1708-1c28-11e5-9a21-1697f925ec7b` accepts `0x01`/`0x00` writes for
on/off control (per the OpenMQTTGateway community reverse-engineering
thread linked below). The advertisement itself carries no payload beyond
the service UUID and the local name.

### Local Name

The advertised local name is the **printed serial number** of the unit —
typically a 9-digit numeric string such as `412201397`. This is a stable
per-unit identifier baked into firmware/EEPROM at manufacture.

```
<numeric serial number>
```

User-renaming the unit is not supported in the brand apps; the serial is
always what's broadcast.

### Advertisement Behavior

- Advertises continuously while the transformer is powered.
- No manufacturer data; no service data — only the service UUID and the
  serial number in the local name.
- Control happens through an unencrypted GATT write characteristic; there is
  no MyDyson / cloud-style auth, which is why the OMG / Theengs community
  has been able to integrate these without proprietary credentials.

## Identification

- **Primary**: service UUID `3A3E0EAE-EDBF-11E4-90EC-1681E6B88EC1` —
  proprietary enough to fingerprint Lester Smart Transformers with
  effectively zero false-positives.
- **Secondary**: numeric (6–12 digit) local name when present.
- **Device class**: `lighting`.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor identity | service UUID | Lester Electrical (OEM) |
| Product family | service UUID | Smart Transformer |
| Brand skin | (cannot be parsed from BLE alone) | Alliance / Tru-Scapes / Constellation Pro — requires physical inspection |
| Serial number | local name | stable per-unit identifier, suitable for long-term tracking |

## What We Cannot Parse (requires GATT)

- Output state (on / off, dim level)
- Firmware version
- Schedule / timer configuration
- Power draw / load status

## Detection Significance

- Outdoor / landscape-lighting deployment nearby — typical signals are a
  residential property's path/garden lights or a commercial outdoor LED
  installation.
- The serial number is **printed on the transformer enclosure**, so a
  determined observer with physical access can map the BLE-broadcast
  identifier to the visible sticker. Treat the serial as a non-rotating
  unique ID for the unit.
- Older single-zone transformers (Alliance iTimerPro generation, 2015–2020)
  use this protocol. Newer Alliance "Alliance bt" mesh-based RGB/CCT fixtures
  use a different stack (Android package `com.ws.mesh.custom.rgb_cct`).

## References

- Lester Smart Transformers product page —
  <https://www.lesterelectrical.com/products/smart-transformers>
- OpenMQTTGateway community thread (independent UUID + GATT
  characteristic confirmation) —
  <https://community.openmqttgateway.com/t/bt-and-lighting-system-basic-advice/1842/8>
- Alliance Transformer iOS app —
  <https://apps.apple.com/us/app/alliance-transformer/id1053543813>
- Constellation Pro iOS app —
  <https://apps.apple.com/us/app/constellation-pro/id1273815799>
- Tru-Scapes Smart Lighting iOS app —
  <https://apps.apple.com/us/app/tru-scapes-smart-lighting/id1331987368>
- Tru-Scapes BT App Reset Instructions (documents the "tap the serial
  number matching the sticker on the transformer" pairing flow) —
  <https://tru-scapes.com/wp-content/uploads/2025/06/Tru-Scapes-BT-App-Reset-Instructions.pdf>
