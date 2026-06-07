# Triones / Zengge OEM LED Controller Plugin

## Overview

"Triones" is the canonical retail brand for a long-lived Zengge OEM firmware embedded in low-cost RGB / RGBW LED strip controllers, "magic" Bluetooth bulbs, and accent lights. The same firmware family ships under dozens of resold aliases — Magic Blue, HappyLighting, LEDBLE, LEDnet, LEDBlue, ALED, AVERYSHOP, EPBOWPT, HaoDeng, MCWOFI, PHOPOLLO, SUPERNIGHT, Zerproc, and others enumerated by the Home Assistant [`led_ble`](https://www.home-assistant.io/integrations/led_ble/) integration. All variants drive the strip through a Zengge GATT control service (0xFFD5 / 0xFFD9) that only appears after pairing; the BLE advertisement itself carries **only a local name** with a fixed prefix and a firmware-baked 12-hex factory ID.

This parser identifies the controller family from the local-name prefix, extracts the 12-hex factory ID as a stable per-unit fingerprint, and attributes the vendor to Zengge.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `^(?i)(Triones:|LEDBLE-|LEDnetWF|LEDnet|LEDBlue-)[0-9A-Fa-f]{12}$` |
| Company ID | _absent_ — no manufacturer-specific data in the advertisement. |
| Service UUIDs | _absent_ — 0xFFD5 control service is post-connect only. |

### Local Name Format

`<PREFIX><12-hex factory ID>`

- `<PREFIX>` is one of `Triones:`, `LEDBLE-`, `LEDnetWF`, `LEDnet`, `LEDBlue-`. Match is case-insensitive — ha-triones [matches on `device.name.lower().startswith("triones")`](https://github.com/sysofwan/ha-triones). `LEDnetWF` is the Wi-Fi co-radio variant of the LEDnet firmware — it must be matched before `LEDnet` so prefix detection picks the longer name and the 12-hex suffix lines up.
- `<12-hex factory ID>` is a firmware-baked identifier stamped at the Zengge factory. **It is NOT the radio's BD_ADDR.** Real captures show prefixes like `22:15:22:00:1?:??` (with `22-15-22` and `42-15-22` not present in the IEEE OUI registry), and the BLE advertisement uses a random address type whose first-byte top bits don't conform to a random static / non-resolvable private layout. The hex tail persists across reboots and factory resets even though the radio MAC rotates.

Examples (real captures, `research/nearsight_export 3.json`):
- `Triones:2215220010D0` → family `Triones`, factory_id `2215220010D0`
- `Triones:4215220013B9` → family `Triones`, factory_id `4215220013B9`

Sibling captures:
- `LEDnetWF000033C60E3F` → family `LEDnetWF` (real capture, `research/nearsight_export 2.json`) — Wi-Fi co-radio variant
- `LEDBLE-1A2B3C4D5E6F` → family `LEDBLE` (documented but not observed locally)
- `LEDnet112233445566` → family `LEDnet` (documented but not observed locally)

The conservative prefix subset deliberately excludes broader globs (`AP-*`, `Dream~*`, `QHM-*`) used by `led_ble`'s manifest — those overlap unrelated devices and would generate false positives. Add them as captures warrant.

## Detection Significance

- **Stable per-unit fingerprint.** The 12-hex factory ID is the persistent identifier — radio MAC is random and rotates, but the local-name suffix doesn't. For tracking purposes this is the device's de-facto serial number.
- **Always-on advertiser.** The controller advertises whenever it's powered, regardless of LED on/off state — "off" only drives PWM to zero; the radio stays up. Cutting mains power is the only way to silence it.
- **No pairing, no whitelist.** GATT is open; any nearby device can connect and drive the strip. Several reverse-engineering writeups call this out as a hardening gap.
- **Density signal.** Clusters of Triones / LEDBLE advertisements correlate with consumer-grade smart-lighting deployments — apartments, gaming setups, dorm rooms, retail accent lighting.

## What We Cannot Parse from Advertisements

- Current RGB color / brightness / animation mode — all state lives behind the 0xFFD5 control service, only readable after a GATT connect (the Zengge firmware doesn't notify state in advertisements).
- Power state (on/off) — the advertisement is identical whether the lights are on or off; only PWM duty changes.
- Firmware version / chipset variant — surfaced over GATT only.
- Companion app / cloud account binding — not present anywhere in the BLE plane.

## References

- [madhead/saberlight — Triones protocol writeup](https://github.com/madhead/saberlight/blob/master/protocols/Triones/protocol.md) — canonical reverse-engineered GATT spec
- [sysofwan/ha-triones](https://github.com/sysofwan/ha-triones) — Home Assistant custom component; discovery logic in `triones.py`
- [home-assistant.io/integrations/led_ble](https://www.home-assistant.io/integrations/led_ble/) + [Bluetooth-Devices/led-ble](https://github.com/Bluetooth-Devices/led-ble) — native HA integration covering the broader Zengge OEM family
- [8none1/pytrionesmqtt](https://github.com/8none1/pytrionesmqtt) — MQTT bridge with service-map diagram
- [Aritzherrero4/python-trionesControl](https://github.com/Aritzherrero4/python-trionesControl) — minimal Python control library
- [Depau/consmart-ble-mqtt](https://github.com/Depau/consmart-ble-mqtt) — covers Consmart / Triones / Flyidea sibling firmwares
- [linuxthings.co.uk — Controlling Bluetooth LED backlights](https://linuxthings.co.uk/blog/controlling-bluetooth-led-backlights-from-linux) — Nexillumi / QHM teardown
- [Bluetooth SIG company identifiers (YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — Zengge not assigned (confirms no company-ID-based detection path).
