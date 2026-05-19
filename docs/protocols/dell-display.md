# Dell BLE-Enabled Display Plugin

## Overview

Several Dell UltraSharp / Professional monitors (the P-series 24" and 27" panels, the C-series video-conferencing displays, and the Premier Color UP-series) expose a BLE service that the **Dell Display Manager** and **Dell Peripheral Manager** desktop apps use to:

- Identify the monitor's firmware revision.
- Switch input source between HDMI / DisplayPort / USB-C.
- Configure KVM and USB-C power-delivery profiles.
- Trigger preset color modes.

The fingerprint is a proprietary 128-bit service UUID; the local name (when broadcast) gives away the marketing model.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `60054001-F97C-C5A3-9941-1C799C307DDF` | Dell's vendor-allocated service UUID. |
| Local name | `^[CPSU]\d{3,4}[A-Z]?\d{3}$` (optional) | E.g. `"P2417027"` (P2417 model, unit 027). |

### Manufacturer Data

8 bytes, mostly zero, with a single varying byte at offset 6:

```
01 01 00 00 00 00 XX 00
                  ^^ varies: 0x89, 0x9A, 0xC9, ...
```

The varying byte is stable within a single sighting burst but changes between captures of the same monitor, so it appears to encode a transient state — likely current input source, brightness step, or power-save phase. The exact semantics are unconfirmed. We surface it as `payload_byte`.

### Local Name Format

The Dell display naming convention is `<model><unit serial>`:

- `P2417027` → model `P2417` (UltraSharp 24"), unit 027.
- C-series and U-series follow the same pattern.

## Detection Significance

- **Office desks / conference rooms.** A cluster of `60054001-…` advertisements is a strong signal that you're scanning near a Dell-equipped workstation row or huddle room.
- **Model fingerprinting.** The model embedded in the local name lets you survey a building's monitor fleet (24" UltraSharp vs. 27" C-series) without physically inspecting each desk.

## What We Cannot Parse from Advertisements

- Live monitor configuration (input source, brightness, color preset) — the apps read those over the GATT connection.
- Firmware revision — same; reachable via a GATT characteristic but not in the advertisement.

## References

- [Dell Display Manager 2 (Windows / macOS)](https://www.dell.com/support/contents/en-us/article/product-support/self-support-knowledgebase/software-and-downloads/dell-display-manager)
- [Dell Peripheral Manager](https://www.dell.com/support/manuals/en-us/dell-peripheral-manager/dpem_userguide)
