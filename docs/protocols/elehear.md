# ELEHEAR Hearing Aids Plugin

## Overview

[ELEHEAR](https://elehear.com/) is an FDA-registered OTC hearing-aid brand (founded 2017 by Eric Miao, manufactured by **Xiamen Wenatong Medical Technology Co., Ltd.**, US ops in Minneapolis). Product lineup:

- **Alpha** / **Alpha Pro** — Bluetooth 5.3 receiver-in-canal (RIC). FCC ID `2A2EV-RIC01`.
- **Beyond** — original 2023 flagship. FCC ID `2BF4W-RIC03`.
- **Beyond Pro** — July 2025 flagship ("VOCCLEAR 2.0").

The aid advertises with what looks like Bluetooth SIG company ID `0x2907` — but this value is **not** in the SIG-assigned list (the current maximum is `0x10C7`). ELEHEAR / Wenatong has not registered for SIG membership; the firmware just emits `0x2907` as a fixed vendor magic in the manufacturer-data slot. We treat it as a **pseudo-company-ID** disambiguator and additionally require the `"ELEHEAR "` local-name prefix.

This is **not** Apple MFi Hearing Aid / Google ASHA. Those protocols carry their identifier as a 16-bit **service-data** UUID (`0xFDF0` for ASHA), not manufacturer-specific data. ELEHEAR Beyond pairs over generic MFi audio streaming, not ASHA.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Pseudo company ID | `0x2907` (**unregistered** — vendor magic, not SIG-assigned) |
| Local name | `^ELEHEAR ` (often truncated — see below) |

### Manufacturer Data Layout (7 bytes total: 2-byte CID + 5-byte payload)

```
Bytes 0..1: 29 07            ← pseudo company ID in little-endian wire order
Bytes 2..6: device token     ← opaque 5-byte per-unit identifier;
                                exposed as `device_token` in metadata.
```

### Local Name Truncation

`"ELEHEAR Beyond Pr"` (17 chars) is the on-air form of the marketing name `"ELEHEAR Beyond Pro"` (18 chars). The 31-byte BLE adv PDU runs out of room once the manufacturer-data AD is also included, so the firmware ships a *short* local name truncated to 17 chars and only emits the full `"Beyond Pro"` via GATT after connection (Apple developer-forum thread 19381 documents this caching behaviour). We surface the on-air name verbatim — UIs that want the full marketing name can map model `"Beyond Pr"` → `"Beyond Pro"`.

### Local Name Format

`ELEHEAR <model>`

Observed model tokens: `Alpha`, `Alpha Pro`, `Beyond`, `Beyond Pr` (truncated `Beyond Pro`).

## Detection Significance

- **Quiet but persistent.** OTC hearing aids advertise continuously while powered on so the ELEHEAR app can reconnect. A stable hearing-aid signal in a residential capture is informative (occupancy / wearer presence).
- **Per-unit fingerprint via `device_token`.** The 5-byte token in the mdata is stable across consecutive advertisements within a single boot cycle. (We haven't confirmed whether it survives a power cycle — assume it does not until additional captures are gathered.)

## What We Cannot Parse from Advertisements

- Volume / preset / fitting parameters — all configured through the ELEHEAR app over GATT.
- Battery level — not advertised; available post-connect.
- Wearer's hearing profile — never exposed over BLE.

## References

- [ELEHEAR Beyond Pro product page](https://elehear.com/products/beyond-pro)
- [HearingTracker review — ELEHEAR Beyond Pro](https://www.hearingtracker.com/hearing-aids/elehear-beyond-pro)
- [FCC ID 2BF4W-RIC03 (Beyond)](https://fcc.report/FCC-ID/2BF4W-RIC03/7434570.pdf)
- [FCC ID 2A2EV-RIC01 (Alpha Pro)](https://fcc.report/FCC-ID/2A2EV-RIC01/6423983.pdf)
- [Apple developer forum thread 19381 — BLE local-name truncation / caching](https://developer.apple.com/forums/thread/19381)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms `0x2907` is not assigned.
