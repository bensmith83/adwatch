# Astera AsteraBox WIFI (ART7-WIFI) Plugin

## Overview

The **AsteraBox WIFI**, model code **ART7-WIFI**, is the Wi-Fi-enabled successor to the original **AsteraBox** from [Astera LED Technology GmbH](https://astera-led.com/) (Munich, Germany). Astera is a specialist manufacturer of battery-powered LED fixtures for professional film, television, broadcast, and live-event lighting — their product line includes the **Titan Tube**, **Helios Tube**, **Hyperion Tube**, **NYX Bulb**, **PlutoFresnel**, **LeoFresnel**, **HydraPanel**, **PixelBrick**, and the **AX-series** PowerPAR / TriplePAR / SpotMax / LightDrop / PixelBars fixtures, all of which are remotely controlled either through the **AsteraApp** on iPad / iPhone or via wireless DMX from a lighting console.

The AsteraBox is the on-set bridge that ties those control surfaces to the fixtures. Internally the ART7-WIFI bundles three radios:

- A **LumenRadio CRMX** 2.4 GHz radio that streams wireless DMX-512 to compatible fixtures (Astera's lamps, plus any other CRMX-capable lights on the rig).
- A **Bluetooth Low Energy** radio that lets the AsteraApp on iPad / iPhone reach the same fleet without needing to be on the rig's Wi-Fi.
- A **Wi-Fi** radio (the "WIFI" half of the product code) that adds an IP-based control path for the AsteraApp. This is the headline upgrade over the original AsteraBox, which is BLE-only on the app side.

A microphone on the bottom of the unit enables music-triggered lighting programs. The internal battery is rated for up to 60 h when only the app-side radios are in use, or up to 18 h with CRMX active. The box ships with a charger and a carry case (it accepts a 7" tablet alongside the unit).

The marketing name varies across resellers ("AsteraBox WIFI", "AsteraBox Wi-Fi CRMX Transmitter Box") but the stamped model code is always **ART7-WIFI**, and that's what shows up in the BLE local-name field.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `ART7WIFI <8-digit serial> ` — note the **trailing space** observed in captures, and the 8-digit zero-padded serial (e.g. `"ART7WIFI 00102101 "`). |
| Manufacturer data | None observed. |
| Service UUIDs | None observed. |
| Service data | Optional `{"2A8C": "02"}` — see below. |
| Address type | Random. |

We anchor strictly on the `^ART7WIFI ` prefix plus a 6+ digit decimal serial (with optional trailing whitespace) so we don't sweep up unrelated devices whose names happen to begin with "ART7" (e.g. some ArtNet bridges, the bare "ART7" without WIFI, etc.). The legacy AsteraBox uses a different name prefix (`AsteraBox <serial>`) and is parsed by [AsteraBoxParser](./asterabox.md).

### The 2A8C oddity

UUID `2A8C` is the **GAP Gender characteristic** in the Bluetooth SIG's [characteristic-UUID registry](https://www.bluetooth.com/specifications/assigned-numbers/), with permitted values `0x00 = unknown`, `0x01 = male`, `0x02 = female`. It is intended to live as a GATT characteristic on a connected device (e.g. a fitness tracker reporting its wearer's gender), not as a service-data slot in an advertisement. The captured ART7-WIFI advertisement places a single `0x02` byte in the service-data slot keyed by `2A8C`. This is almost certainly a firmware bug or a vendor mis-using a convenient short UUID for an opaque 1-byte indicator — there is no plausible Astera-product-related interpretation of "female" in that context.

We capture the byte verbatim in metadata as `service_data_2a8c` but do **not** interpret it. If later samples show the byte cycling (0x00 / 0x01 / 0x02) we can revisit; in the current single-emitter / 37-sighting sample it's stable at `0x02` and probably encodes something like firmware mode or battery state.

### Serial number format

The trailing 8-digit numeric is a zero-padded unit serial. The sole observed value `00102101` parses as either decimal `102,101` or, if it's a date-style code, possibly `0010-21-01` (week / day / etc.) — we can't tell from one sample. We treat it as an opaque decimal string and use it as the stable key.

### Stable Key

We use `astera_art7wifi:<serial>` so MAC rotations on the underlying random BD_ADDR collapse to a single physical bridge. This matches the convention used by [AsteraBoxParser](./asterabox.md) for the legacy unit.

## Detection Significance

- **Film / broadcast set marker.** Like the legacy AsteraBox, the AsteraBox WIFI is not consumer kit — it retails around USD 1,500 and is essentially only found in the hands of professional gaffers, DPs, rental houses, and corporate / venue AV departments. A sighting in a residential or commercial scan strongly suggests a film, video, photo, or live-event shoot is underway nearby, **or** that the device has been semi-permanently installed as part of a venue's AV infrastructure.
- **The 37-sighting sustained presence is informative.** In our first capture the unit was seen 37 times over a continuous ~24 h window in the Fenway area of Boston, which is inconsistent with a portable on-set use case (rigs usually move). It's more consistent with the box being deployed as **fixed infrastructure** — for example a permanent CRMX-to-Astera-fixtures bridge in a venue's house-light rig, a museum / gallery / corporate-lobby installation, or a video/photo studio's pre-rigged grid.
- **Travels with a fleet.** Where there's an AsteraBox of either generation, there are very likely Astera fixtures within ~50 m. Once those parsers exist, co-occurrence becomes a reliable "Astera kit on site" signal. The legacy and WIFI parsers share `deviceClass = "lighting_controller"` and an `Astera` vendor field, so a downstream "Astera presence" rollup can union them by vendor.
- **Rare and stable.** Per-unit serials are engraved on the case and don't change. The 8-digit serial is a robust per-device key for fleet tracking — useful for spotting the same rental box returning to different locations over time, or for confirming a particular installed unit.

## What We Cannot Parse from Advertisements

- **DMX universe / channel assignments.** The CRMX side is a separate radio entirely and isn't visible to BLE scanners.
- **Battery level.** The unit has a built-in battery but does not surface charge state in its advertisement.
- **Connected fixtures.** Which Astera lamps the box is currently bridging — not exposed.
- **Firmware version.** Not in the advertisement; only available via GATT through the AsteraApp.
- **Wi-Fi connection state.** Whether the Wi-Fi radio is associated to an AP or running its own SoftAP for app provisioning — not exposed.
- **GPS / location.** Astera doesn't ship any location reporting in the BLE advertisement.
- **The `2A8C` byte's meaning.** See above — we capture it but don't interpret.

## References

- [Astera AsteraBox product page](https://astera-led.com/products/asterabox/)
- [B&H Photo — Astera AsteraBox Wi-Fi CRMX Transmitter Box ART7-WIFI](https://www.bhphotovideo.com/c/product/1823781-REG/astera_art7_wifi_asterabox_wi_fi_crmx_transmitter.html)
- [Manuals+ — AsteraBox WIFI (ART7-WIFI) User Manual and Technical Specifications](https://manuals.plus/m/e42d099314094397bdd7d13ad3e7ac84347395743860c87e855f365641f57e96)
- [NLFX Pro — ART7-WIFI AsteraBox: Enhanced Wireless Control for Astera Lighting](https://www.nlfxpro.com/art7-wifi-asterabox/)
- [MACCAM — Astera ART7-WIFI AsteraBox CRMX Transmitter Box](https://www.maccam.tv/products/astera-art7-wifi-asterabox-art7-wifi-connect-phone-or-tablet-via-crmx-bluetooth-uhf-wifi-to-control-astera-lights-via-astera-app-or-wireless-dmx-comes-with-charger-and-carry-case-fits-7-tablet-inside)
- [Astera product line](https://astera-led.com/products/) — companion fixtures likely to co-occur (Titan Tube, NYX Bulb, etc.).
- [Bluetooth SIG Assigned Numbers — characteristics](https://www.bluetooth.com/specifications/assigned-numbers/) — UUID `2A8C` (Gender) reference.
- Legacy companion parser: [asterabox.md](./asterabox.md).
