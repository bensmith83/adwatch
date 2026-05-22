# TUNAI Bluetooth Audio Receivers (Firefly LDAC) Plugin

## Overview

**TUNAI Creative Inc.** is a Taiwan-based consumer-audio brand (founded 2014, with the consumer line launching around 2016) that specializes in compact Bluetooth and wireless audio accessories aimed at audiophile and in-car listening niches. Their flagship today is the **TUNAI Firefly LDAC**, a thumbnail-sized Bluetooth 5.0 receiver / DAC dongle that plugs into any 3.5 mm AUX input (car head-unit, home stereo, powered monitors) and adds wireless high-resolution audio over Sony's **LDAC** codec — the codec that streams at up to 990 kbps and is the de-facto high-res standard on Android, well beyond what stock SBC, AAC, or even aptX HD can carry.

The Firefly LDAC pairs an LDAC-capable Bluetooth front end with a **Cirrus Logic audiophile DAC** (127 dB SNR) and a built-in ground-loop isolator, which is the practical pitch: it gives an aging in-car AUX jack roughly the wireless-audio quality of a modern OEM head-unit at a fraction of the price. It also auto-pairs to the last device on power-up (driven by the car's accessory bus, so no charging is needed) and supports two simultaneous source devices for music-handoff.

The wider TUNAI product family includes:

| Product | Category | Notes |
|---|---|---|
| **Firefly** (original) | BT receiver | AAC / SBC, no LDAC. |
| **Firefly LDAC** | BT receiver | LDAC + AAC, Cirrus DAC. The product this parser was written from. |
| **Firefly Chat** | BT receiver | LDAC variant with a microphone for hands-free calls. |
| **Drum** | In-ear earphones | Audiophile IEMs (JAS Hi-Res certified). |
| **Bumper** | Accessory | Carry / mounting accessory in the Firefly ecosystem. |
| **Clip, Square, Button** | Various | Older / sibling Bluetooth audio accessories. |

This parser is a **single-sighting** plugin and we are honest about that limitation — see "What We Cannot Parse" below.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `APP TUNAI FIREFLY LDAC` (observed) or `TUNAI FIREFLY LDAC` (hypothesized always-on form). Other model tokens (`DRUM`, `BUMPER`) follow the same shape. |
| Manufacturer data | None observed. |
| Service UUIDs | None observed. |
| Service data | None observed. |
| Address type | Random (rotated). |

We anchor on a strict case-sensitive regex `^(APP )?TUNAI ([A-Z]+(?: LDAC)?)$` so we only match the all-caps TUNAI product line. Lower-case variants such as `LE-Tunai Firefly` (some third-party adapters that piggyback on a similar name shape) are intentionally not matched.

### Local Name Format

The sole sighting in `adwatch_export 9.json` shows:

```
name=APP TUNAI FIREFLY LDAC   mfg=nil   svc=nil   uuids=nil
```

The leading `APP ` token is the TUNAI **Connect-app pairing-mode** broadcast — the device exposes itself this way when the user has put it into discovery mode from the companion app (TUNAI Connect, available on iOS and Android, used for EQ / firmware / ground-loop-isolator settings). When the device is in normal operation (e.g. powered up in a car and auto-pairing to the last source), we hypothesize the prefix is absent and the name reduces to `TUNAI FIREFLY LDAC`. Both shapes are parsed and the prefix presence is encoded in `metadata["broadcast_mode"]`:

- `"app_pairing"` — `APP ` prefix present; device is in companion-app discovery.
- `"normal"` — no prefix; presumed normal / paired operation.

The `"normal"` shape is currently **unconfirmed** from captures — see "What We Cannot Parse".

### Product Map

We extract the model token from the captured group and format it Title-case with `LDAC` left upper-cased:

| Local name | `metadata["model"]` |
|---|---|
| `APP TUNAI FIREFLY LDAC` | `Firefly LDAC` |
| `TUNAI FIREFLY LDAC` | `Firefly LDAC` |
| `APP TUNAI DRUM` | `Drum` |
| `TUNAI BUMPER` | `Bumper` |

### Stable Key

**`stableKey = nil`** — the advertisement carries no per-device serial, MAC the device exposes is random / rotated, and there's no manufacturer-data token to pin against. Two physical Firefly LDAC units in the same car park would be indistinguishable from each other from advertisements alone. Downstream consumers that need short-term tracking can use `mac+name`, but that key will roll whenever the random BD_ADDR rotates.

This matches the convention used by other strict-name-only parsers in this repo (e.g. `LGTVParser`, `BP5SParser`).

## Detection Significance

- **Audiophile household / portable hi-fi tell.** LDAC-capable Bluetooth receivers are an audiophile-niche product — most car owners are happy with the OEM AAC/SBC Bluetooth in their head-unit, and the people who care enough to bolt on a USD ~60 third-party dongle to get LDAC are the ones who also own LDAC-capable source devices (Sony Walkman, certain Android flagships, FiiO DAPs). A sighting in a residential / vehicle scan is a weak but real signal of an audiophile listener.
- **In-car listening posture.** The Firefly LDAC's auto-pair-on-power feature is specifically engineered for the car-AUX use case — the device powers up with the accessory bus, auto-connects, and starts streaming. A sustained sighting in a parking-lot scan is much more likely to be a car-installed unit than a stationary one.
- **Co-occurrence with hi-res sources.** Where there's a Firefly LDAC, there's typically a Sony / Android source nearby running LDAC. Pairing this signal with other audiophile-niche parsers (Astell&Kern, Sony Walkman) is more informative than the TUNAI sighting alone.

## What We Cannot Parse from Advertisements

- **Codec in use** (LDAC vs AAC vs SBC). Not surfaced in the advertisement.
- **Battery / power state.** The Firefly LDAC is bus-powered, but no power state is exposed in BLE.
- **Paired source devices.** Whether the dongle is currently bonded to a phone, and to which one.
- **Firmware / version.** Not in the advertisement; only available via the TUNAI Connect companion app.
- **Per-unit serial / stable identity.** No serial in the broadcast — see "Stable Key" above.
- **The "normal" / paired-mode broadcast shape.** This parser **assumes** the always-on broadcast drops the `APP ` prefix. We have not seen a non-`APP` capture; if TUNAI's firmware actually keeps the `APP ` prefix even in normal operation, the `"normal"` branch of this parser will never fire. This is fine — `"app_pairing"` parses correctly either way.
- **Bumper as a BLE device.** TUNAI Bumper is listed as an accessory in TUNAI's lineup; we have not independently confirmed whether it advertises BLE at all. The parser handles the name shape on the off chance it does, but this branch is speculative.

## References

- [Amazon — TUNAI Firefly LDAC Bluetooth Receiver](https://www.amazon.com/Firefly-Bluetooth-Receiver-Smallest-Streaming/dp/B01HDO66NK) — product listing and feature spec.
- [Frieve Audio Review — TUNAI Firefly LDAC](https://audioreview.frieve.com/products/en/tunai-firefly-ldac/) — independent technical review.
- [Amazon — TUNAI Firefly Chat (LDAC + microphone variant)](https://www.amazon.com/Firefly-Chat-Bluetooth-Receiver-Hands-Free/dp/B07C78WV6J) — sibling product.
- [Kickstarter — TUNAI DRUM Audiophile Earphones](https://www.kickstarter.com/projects/398634494/drum-high-resolution-bass-enhanced-audiophile-earp) — DRUM product page.
- [12volt-shop — TUNAI brand catalog](https://12volt-shop.com/en/tunai/) — Taiwan-based brand overview, in-car-audio positioning.
