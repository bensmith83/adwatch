# SP110E / SP-series LED Controller Plugin

> **2026-07-06 sweep:** generalized from the single `SP110E` name to the
> **SP-series** (`SP110E`, `SP601E`, …) — all Shenzhen addressable-LED
> controllers sharing the `SP<digits><letter>` name + `FFB0` control service.
> The model is surfaced from the name. `SP601E` advertises a vanity CID `0x5053`
> whose bytes spell **"SP"** (vs SP110E's `0x0000` placeholder), but matching
> still anchors on **name + FFB0, never the CID** (FFB0 is shared by unrelated
> Shenzhen LED controllers). Parser id stays `sp110e_led` for continuity.
> (SP601E was low-trust-sourced — see the sweep write-up.)

## Overview

The **SP110E** is an inexpensive single-channel SPI / addressable-LED
controller — the cheap go-to driver for **WS2812 / SK6812 / SM16703 / WS2811**
strips and similar. The hardware is BLE-only (no Wi-Fi), and is sold under a
handful of brand names that share one Shenzhen OEM design:

- **iLightsIn** — the most common front-of-box brand on AliExpress/Amazon.
- **Magic Hue** — the brand on the box that the dominant Android/iOS app
  ("LedChord" / "LotusLantern" / "BLE LED Controller") talks to.
- Generic **SP-LED-CONTROLLER** / **SP110E** SKUs from unbranded resellers.

The vendor (Shenzhen LeLight Technology and a handful of resellers around it)
has never registered with the Bluetooth SIG, so the company ID in the
advertisement is the placeholder `0x0000`. Identification therefore anchors
on the fixed local name `SP110E` plus the `FFB0` service UUID that exposes
the control characteristics over GATT.

This is a "maker / home-DIY LED rig" beacon. A sighting almost always
indicates an LED-strip project (under-counter lights, holiday lights, room
accent strips, cosplay/prop builds) within a few meters.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Local name | `SP110E` (fixed — no per-device suffix or serial) |
| Service UUIDs | `0xFFB0` (control service — same UUID is used by a handful of other generic Chinese WS2812 BLE controllers, so we anchor on name **and** service together) |
| Company ID | `0x0000` (Bluetooth SIG **placeholder** — vendor never registered; collides with every other unregistered vendor, so cannot be used as a primary key) |
| Address type | Random |

Because `0x0000` is a meaningless collision-magnet and `FFB0` overlaps with
other generic LED controllers, we require **both** `localName == "SP110E"` and
the `FFB0` service UUID before claiming the advertisement.

### Manufacturer Data Layout (10 bytes)

```
Bytes 0..1   : 00 00                   ← LE company ID (0x0000 placeholder)
Bytes 2..9   : 00 00 a9 9a 18 04 48 b9 ← opaque 8-byte payload
```

The 8-byte payload after the CID very likely encodes some mix of MAC
suffix / serial bytes + a firmware version / build tag, but no public
decoder ties specific bytes to specific fields. We surface the full payload
verbatim as `payload_hex` for downstream analysis and let stable-key dedup
fall back to the (random) BD_ADDR.

### Stable Key

We use `sp110e_led:<macAddress>` — there is no in-advertisement identifier
strong enough to survive a MAC rotation, so the per-scan random address is
the best we have. If a controller stays in range long enough for a parsed
record to land before its address rotates, it will collapse to one stable
entity for that session.

## Detection Significance

- **Cheap / common in DIY scenes.** SP110E is a default pick for hobbyist
  LED rigs because it costs <$10 and the LedChord app is free. Expect to
  see it in maker households, cosplay/film communities, and student housing
  with under-counter or behind-TV strips.
- **Always-on.** The controller advertises continuously while powered,
  even when the LED output is off and the app is closed — so the beacon
  reveals presence of the hardware, not active use.
- **No PII.** The advertisement carries no user-tied identifier (no MAC of
  a paired phone, no SSID echo). It is a "device exists here" beacon only.

## What We Cannot Parse from Advertisements

- **LED state, colour, brightness, pattern, animation speed.** These are
  written via GATT over the `FFB0` service while the app is connected;
  they never appear in advertisements.
- **Chip type / strip configuration** (WS2812 vs SK6812 vs SM16703…) — a
  GATT-readable configuration block, not advertised.
- **Firmware version / model variant.** Likely encoded inside the opaque
  8-byte payload, but no public decoder. A controlled-experiment capture
  (multiple SP110E units side-by-side from different production batches)
  would let us correlate which bytes are stable per-firmware vs per-unit.

## References

- [QuinLED — "SP110E review"](https://quinled.info/) — independent review;
  documents the controller's hardware, packaging, and the LedChord app.
- [Bluetooth SIG company identifiers](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
  — confirms `0x0000` is a placeholder, not an assignment.
- LedChord / LotusLantern / "BLE LED Controller" — the dominant
  Android/iOS apps that drive the controller over GATT on `FFB0`.
- Various community write-ups under the GitHub search "SP110E BLE"
  document the GATT control protocol (LED state, colour, pattern) which
  is out of scope for advertisement-only parsing.
