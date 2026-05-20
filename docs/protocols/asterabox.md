# AsteraBox Plugin

## Overview

The **AsteraBox** is a portable wireless DMX bridge / transmitter from [Astera LED Technology GmbH](https://astera-led.com/) (Munich, Germany), a specialist manufacturer of battery-powered LED fixtures for professional film, broadcast, and live-event lighting. Astera's product line includes the **Titan Tube**, **Helios Tube**, **NYX Bulb**, and **PlutoFresnel** fixtures, all of which are remotely controlled either through the iPad-based **AsteraApp** or via wireless DMX from a console.

The AsteraBox is the on-set bridge that ties those control surfaces to the fixtures. Internally it bundles two radios:

- A **LumenRadio CRMX** 2.4 GHz transmitter that streams wireless DMX-512 to compatible fixtures (Astera's lamps, plus any other CRMX-capable lights on the rig).
- A **Bluetooth Low Energy** radio that lets the AsteraApp on iPad/iPhone reach the same fleet without needing to be on the rig's Wi-Fi.

The successor **AsteraBox WIFI** adds a Wi-Fi radio for app-side connectivity but otherwise advertises the same family.

In our captures the AsteraBox advertises a **local name only** — no manufacturer data and no service data have been observed. The local name is shaped:

```
AsteraBox <serial>
```

where `<serial>` is the 6-digit decimal unit number engraved on the case (e.g. `"AsteraBox 910757"`).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `AsteraBox <6+ digit serial>` (e.g. `"AsteraBox 910757"`) |
| Manufacturer data | None observed |
| Service data | None observed |
| Service UUIDs | None observed |
| Address type | Random |

We anchor strictly on the `^AsteraBox ` prefix plus a 4+ digit decimal trailer. The strictness is deliberate: Astera's individual lamps (Titan Tube, Helios Tube, NYX Bulb, PlutoFresnel) almost certainly advertise under different names, and with only one sample we don't want to sweep them up under the wrong parser. Those will be tracked by separate parsers as samples land.

### Stable Key

We use `asterabox:<serial>` so MAC rotations on the underlying random BD_ADDR collapse to a single physical bridge.

## Detection Significance

- **Film / broadcast set marker.** AsteraBoxes are not consumer kit — they retail at roughly EUR 1,200 and are essentially only found in the hands of professional gaffers, DPs, and rental houses. A sighting in a residential or commercial scan strongly suggests a film, video, photo, or live-event shoot is underway nearby.
- **Travels with a fleet.** An AsteraBox is the head of a small-to-large lighting rig; if you see one, there are very likely also Titan Tubes, NYX Bulbs, or similar fixtures within ~50 m. Once those parsers exist, co-occurrence becomes a reliable "Astera kit on set" signal.
- **Rare and stable.** Per-unit serials are engraved on the case and don't change. The trailing 6-digit number is a robust per-device key for fleet tracking — useful for spotting the same rental box returning to different locations over time.

## What We Cannot Parse from Advertisements

- **DMX universe / channel assignments.** The CRMX side is a separate radio entirely and isn't visible to BLE scanners.
- **Battery level.** The AsteraBox has a built-in battery (rated ~20 h) but does not surface charge state in its advertisement.
- **Connected fixtures.** Which Astera lamps the box is currently bridging — not exposed.
- **Firmware version.** Not in the advertisement; only available via GATT through the AsteraApp.
- **GPS / location.** Astera doesn't ship any location reporting in the BLE advertisement.

## References

- [AsteraBox product page](https://astera-led.com/products/asterabox/)
- [Astera product line](https://astera-led.com/products/)
- [Astera firmware release notes](https://update.astera-led.com/firmwares/current/release_notes.html)
- [NYX Bulb product page](https://astera-led.com/products/nyx-bulb/) — companion fixture; likely future co-occurrence signal.
- [Helios Tube product page](https://astera-led.com/products/helios-tube/)
