# Poly BT700 Plugin

## Overview

The **Poly BT700** is a USB-A / USB-C Bluetooth audio dongle from [HP Poly](https://www.hp.com/us-en/poly/accessories/headsets-and-speakerphones/poly-bt700-usb-bluetooth-adapter.html) — the merged identity of HP and Plantronics following HP's 2022 acquisition of Poly (which itself was the merged Plantronics + Polycom). The BT700 ships in enterprise unified-comms bundles for Microsoft Teams and Zoom, pairing PC-side software with Poly **Voyager Focus 2 UC**, **Voyager Free 60**, **Savi 8200**, and similar wireless headsets without traversing the host's onboard Bluetooth stack.

The BT600 / BT600C are the immediate predecessor SKUs (the trailing `C` indicates the USB-C variant) and share the same advertising shape. The headsets that pair *to* the dongle advertise under their own product names and are tracked by separate parsers.

This parser identifies the **dongle itself**, not the paired headset.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer data | *(none observed)* |
| Service data | *(none observed)* |
| Service UUIDs | *(none observed in our captures)* |
| Local name | `Poly BT<model>` — `Poly BT700`, `Poly BT600`, `Poly BT600C` |
| Address type | random |

No manufacturer-data or service-data shortcut: identification is purely local-name based. The regex anchors on `^Poly BT(\d{3,4}[A-Z]?)$` so we accept the 3-4 digit numeric model with an optional uppercase variant letter, and reject:

- Headsets and speakerphones (`Voyager Focus 2`, `Poly Sync 20`) that pair to the dongle.
- Truncated / malformed names (`Poly BT`, `Poly BT7`).

### Stable Key

`poly_bt:<model>:<macAddress>` — the local name carries no per-unit serial, so we scope by MAC address. Two BT700s in the same office produce two distinct stable keys (rather than collapsing into one).

## Detection Significance

- **Workstation / office-presence signal.** A BT700 sighting is a near-perfect proxy for an active or recently-active PC running a UC client (Teams / Zoom / Webex). The dongle is plugged into a host, advertises only when powered, and is rarely seen outside of office, home-office, or call-center environments.
- **Enterprise procurement footprint.** Poly BT-series dongles ship in IT-procured bundles; a cluster of them in a venue indicates a managed-IT deployment (vs. consumer BYOD).
- **Headset linkage.** When a BT700 is sighted alongside a Voyager / Savi / Voyager Free advertisement, the two are likely paired and belong to the same workstation.

## What We Cannot Parse from Advertisements

- **Per-unit serial number.** Not in the advertisement — stable-key scoping by MAC is the best we can do.
- **Paired headset identity.** The dongle's advertisement carries no reference to the headset it's currently linked to.
- **Call state / mute / volume.** Surfaced over the proprietary HID-over-GATT channel after pairing, not in the unconnectable advertisement.
- **Firmware version.** Not surfaced; only visible via the Poly Lens Desktop companion app over the USB side.

## References

- [Poly BT700 product page (HP)](https://www.hp.com/us-en/poly/accessories/headsets-and-speakerphones/poly-bt700-usb-bluetooth-adapter.html)
- [HP Poly BT-series support index](https://support.hp.com/us-en/poly/bt-series)
- [Poly BT600 (predecessor) product page](https://www.poly.com/us/en/products/headsets/accessories/bt600)
- [FCC ID filings under "BT700" / Plantronics applicant](https://fccid.io/) — search applicant Plantronics / Poly for BT700, BT600.
