# Airoha RACE SDK Audio Devices Plugin

## Overview

The 16-bit-pretending **128-bit** service UUID `5052494D-2DAB-0341-6972-6F6861424C45` is the **Airoha "RACE"** GATT service — hardcoded in the Airoha audio SDK and shipped by every TWS / headphone product that integrates an Airoha-family BLE audio SoC. The UUID's 16 bytes decode to the ASCII sequence "PRIM" + `2D AB 03` + "AirohaBLE", which is Airoha's self-identification convention. The companion characteristics use the same trick:

| UUID | ASCII decode |
|---|---|
| Service `5052494D-2DAB-0341-6972-6F6861424C45` | `PRIM-«☻AirohaBLE` |
| TX char `43484152-2DAB-3241-6972-6F6861424C45` | `CHAR-«2AirohaBLE` |
| RX char `43484152-2DAB-3141-6972-6F6861424C45` | `CHAR-«1AirohaBLE` |

This parser fingerprints any Airoha-SDK device by the service UUID alone, strips the `LE-` prefix that the Airoha dual-mode sample app prepends to the LE-only friendly name, and surfaces a `brand_hint` when the friendly name contains a recognizable consumer-audio brand token.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Service UUID | `5052494D-2DAB-0341-6972-6F6861424C45` | Airoha RACE service. Sufficient by itself. |
| Local name | `^LE-` prefix on dual-mode SKUs | Stripped before exposure as `friendly_name`. Devices that advertise only the LE name without the prefix are also accepted. |
| Company ID | Effectively random | The SDK emits uninitialised / MAC-derived bytes into the manufacturer-data slot. **Do not gate** on company ID — `0xD995`, `0x9279`, `0x4703`, … all appear across different Airoha-based units. |

### Chips that ship this service

The Airoha audio SDK is reused across the **AB155x / AB1562 / AB1568 / AB158x** families (BT 5.x dual-mode + LE Audio TWS SoCs). Bose's 2024 QuietComfort Earbuds use the AB1585; the non-Ultra Bose QC Headphones also appear in the wild advertising this UUID, so the over-ear SKU is Airoha-based as well (though it is **not** covered by Bose's published RACE-vulnerability patch list — that list scopes only to QC Earbuds).

### Why the `LE-` prefix

Airoha's reference dual-mode firmware advertises the same friendly name twice: once over Classic Bluetooth (BR/EDR), and once on the LE-only advertising channel, with the second copy prefixed `LE-` so a pairing UI can disambiguate. OEMs rarely override this, which makes the prefix a strong Airoha-SDK fingerprint on its own (combined with the RACE UUID).

## Detection Significance

- **Catch-all for low-cost audio.** Many Shenzhen-OEM no-name earbuds (lenas beats, Push ANC Active, …) advertise nothing distinctive on the manufacturer-data side but all carry this service UUID — making the parser a useful catch-all for the long tail of consumer audio that other vendor-specific parsers miss.
- **Security-relevant device family.** The RACE protocol was the subject of a 2025 disclosure (ERNW / Insinuator). Surfacing this fingerprint in your scan output is useful for inventory of potentially-affected devices.

## What We Cannot Parse from Advertisements

- Pairing state, ANC mode, battery, EQ — all live over the GATT connection on the RACE service (TX / RX characteristics).
- Volume / play state — same.
- Firmware version — exposed via the standard `0x180A` Device Information service after connect.

## References

- [auracast-research/race-toolkit](https://github.com/auracast-research/race-toolkit) — the only public RACE protocol decoder (works over GATT / RFCOMM / USB HID; does not parse advertisements).
- [ERNW Whitepaper #74 — Airoha RACE vulnerabilities](https://static.ernw.de/whitepaper/ERNW_White_Paper_74_1.0.pdf)
- [Insinuator: full disclosure of Airoha RACE](https://insinuator.net/2025/12/bluetooth-headphone-jacking-full-disclosure-of-airoha-race-vulnerabilities/)
- [Mapaho: Fingerprints in the air](https://www.mapaho.com/en/fingerprints-in-the-air/) — independent confirmation of the UUID-as-vendor-fingerprint pattern.
- [Bose QC Earbuds (2024) teardown — confirms AB1585](https://www.qucox.com/new-quietcomfort-earbuds-teardown/)
