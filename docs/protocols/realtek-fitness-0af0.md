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
| Service UUID | `0x0AF0` | Unregistered; shared across re-brands — **the routing key since 2026-08-30** |
| Company ID | Vendor-varying (`0x1EAB`, `0x1F33`, `0x1DEC`, `0x1E25`, `0x1ECE`, `0x1EED`, ...) | Little-endian in mfg data; per-OEM, so never a sufficient routing key |
| Embedded device ID | 6 bytes | MAC-shaped, stable per unit; every unit seen so far starts `f4` except one |
| Pivot marker | `0x02 0x01` | At offset 8–9 of mfg payload |

### Third-OEM company IDs (2026-08-30 sweep)

The cumulative NearSight telemetry corpus (2026-08-02 → 08-29) held five
nameless units that carry the exact `02 01` pivot frame under company IDs
the parser had never seen, and which therefore never routed to it while
routing was CID-only:

| CID | Frame (mfg data) | First seen | Sightings |
|-----|------------------|------------|-----------|
| `0x1ECE` | `ce 1e xx xx xx xx xx xx  02 01 01 01 01 01` | 2026-08-02 | 2 |
| `0x1EED` | `ed 1e f4 xx xx xx xx xx  02 01 0a 01 01 01` | 2026-08-23 | 2 |
| `0x1DEC` | `ec 1d f4 xx xx xx xx xx  02 01 08 01 01 01` | 2026-08-23 | 7 |
| `0x1E25` | `25 1e f4 xx xx xx xx xx  02 01 05 01 01 01` | 2026-08-28 | 22 |
| `0x1DEC` | `ec 1d f4 xx xx xx xx xx  02 01 08 01 01 01` | 2026-08-29 | 2 |

None of the five CIDs is SIG-assigned. The NearSight parser now routes on
the `0x0AF0` service UUID as well as the two original CIDs (bead
adwatch-app-eawg); the `02 01` pivot gate is unchanged and remains the
actual discriminator.

**Not this family — same UUID, different pivot.** A second product line
advertises `0x0AF0` with a `03 01` pivot and a 16-byte frame:
`7b 1f xx xx xx xx xx xx  03 01 08 08 00 00 00 62` (named `DR05`, a
dashcam — CID `0x1F7B`), `75 1f xx xx xx xx xx xx  03 01 07 08 00 00 00 62`,
`4c 1f xx xx xx xx xx xx  03 01 11 08 00 00 00 62`. The pivot check rejects
these, so the service-UUID route does not over-claim them; they are on the
NearSight watchlist (DR05 dashcam, CID 0x1F7B) as a separate family.

## Ad Format — Manufacturer Data

Observed 14-byte payload (len may vary slightly by firmware):

```
Offset   Bytes                  Meaning
  0-1    ab 1e  (or 33 1f)      Company ID (little-endian)
  2-7    xx xx xx xx xx xx      Embedded device ID (MAC-shaped)
  8-9    02 01                  Fixed pivot / protocol magic
 10      01 | 07 | ...          State / counter byte (varies)
 11-13   01 01 01               Padding (observed constant)
```

### Concrete Samples

- `BIGGERFIVE Brave 2`: `ab 1e f4 xx xx xx xx xx  02 01 07 01 01 01`
- `IDW20`            : `33 1f f4 xx xx xx xx xx  02 01 01 01 01 01`

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
