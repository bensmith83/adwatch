# Realtek / OEM White-label Fitness Watch Protocol (0x0AF0)

## Overview

A family of cheap Chinese BT-calling fitness watches advertise service UUID
`0x0AF0` with a consistent manufacturer-data layout. Observed re-brands:

- **BIGGERFIVE Brave 2** (kids' fitness smartwatch)
- **IDW20** (sold by Fitpolo, TOOBUR, and many others; OEM **Shenzhen MYX Technology Co., Ltd.**)
- Companion apps: **VeryFit** (IDW20), brand-specific apps (BIGGERFIVE)

Neither the company IDs (e.g. `0x1EAB`, `0x1F33`) nor the `0x0AF0` service
UUID are in the Bluetooth SIG assigned-numbers list. The layout appears
baked into a shared OEM firmware — most likely a Realtek-SDK-based reference
design (MAC-shape bytes consistently start with `F4`, a common Realtek OUI
prefix range).

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0x0AF0` | Unregistered; shared across re-brands |
| Company ID | Vendor-varying (`0x1EAB`, `0x1F33`, ...) | Little-endian in mfg data |
| Embedded device ID | 6 bytes | MAC-shaped, stable per unit |
| Pivot marker | `0x02 0x01` | At offset 8–9 of mfg payload |

## Ad Format — Manufacturer Data

Observed 14-byte payload (len may vary slightly by firmware):

```
Offset   Bytes                  Meaning
  0-1    ab 1e  (or 33 1f)      Company ID (little-endian)
  2-7    f4 06 c8 8a 71 36      Embedded device ID (MAC-shaped)
  8-9    02 01                  Fixed pivot / protocol magic
 10      01 | 07 | ...          State / counter byte (varies)
 11-13   01 01 01               Padding (observed constant)
```

### Concrete Samples

- `BIGGERFIVE Brave 2`: `ab 1e f4 06 c8 8a 71 36  02 01 07 01 01 01`
- `IDW20`            : `33 1f f4 3a a2 2d ea 34  02 01 01 01 01 01`

## What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service UUID `0x0AF0` | Watch nearby |
| Vendor CID | mfg bytes 0-1 | Useful for clustering re-brands |
| Stable device ID | mfg bytes 2-7 | Preferable to outer BLE MAC for identity |
| State byte | mfg byte 10 | Semantics unknown; may be charging/worn flag |
| Device name | local_name | Brand / model identifier |

## What We Cannot Parse

- Heart rate, SpO2, step count — require GATT connection to the VeryFit /
  Da Fit / brand-specific characteristic set
- Firmware version, battery level
- User-profile settings

## Identity Hashing

Prefer the **embedded 6-byte ID** over the outer BLE MAC (the outer MAC is
random on many of these watches, whereas the embedded ID is stable):

```
if pivot matches:
    identifier = SHA256("{embedded_id_hex}:realtek_fitness")[:16]
else:
    identifier = SHA256("{mac}:realtek_fitness")[:16]
```

## Detection Significance

- Cheap consumer fitness-tracker watch in range
- Often represents a whole household (kids' watches, gift watches)
- Shared SDK across re-brands makes this one parser valuable across many
  product names

## Parsing Strategy

1. Require service UUID `0x0AF0`.
2. If mfg data ≥ 10 bytes **and** bytes 8-9 == `02 01`, extract fields.
3. Otherwise, record a bare presence sighting (no extracted fields).

## References

- [BIGGERFIVE Brave 2 product page](https://www.biggerfive.com/products/kids-smart-watch-fitness-tracker-for-boys-girls-bw02)
- [Fitpolo IDW20](https://www.fitpolo.net/products/fitpolo-idw20-smart-watch-with-bluetooth-call-answer)
- [IDW20 user manual (confirms VeryFit app)](https://manuals.plus/m/11a81784ac71e14c359311e8d9501b8b7ea1569116829fc5f64da226419a3a11)
- [Shenzhen MYX Technology IDW20 OEM listing](https://myx-technology.en.made-in-china.com/product/DTWRMQfGIgkb/China-2024-New-Idw20-Waterproof-IP68-Bt-5-1-Smartwatch-1-91-Inch-TFT-Screen-Blood-Oxygen-Pressure-Health-Monitoring-Sports-Smart-Watch.html)
- [Nordic bluetooth-numbers-database (SIG CIDs — 0x1EAB, 0x1F33 absent)](https://github.com/NordicSemiconductor/bluetooth-numbers-database/blob/master/v1/company_ids.json)
