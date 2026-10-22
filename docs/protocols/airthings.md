# Airthings Wave (Air Quality Monitor)

## Overview

Airthings makes popular indoor air quality monitors (radon, CO2, VOC, humidity, temperature). Devices broadcast a serial number and model identification in BLE advertisements. Sensor readings require a GATT connection — this parser provides device detection and classification.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0334` (820) | Airthings AS |
| Local name | `AT#NNNNNN-2900Radon` | Wave Gen 1 only; other models may not have distinctive names |

### Manufacturer Data Layout (minimum 4 bytes after company ID)

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0-3 | Serial Number | uint32 LE | 10-digit serial on device label | — |

### Model Identification from Serial Number Prefix

The first 4 digits of the serial number identify the model:

| Prefix | Model | Product Name |
|--------|-------|-------------|
| `2900` | WAVE_GEN_1 | Wave Gen 1 (radon) |
| `2920` | WAVE_MINI | Wave Mini (VOC, temp, humidity) |
| `2930` | WAVE_PLUS | Wave Plus (radon, CO2, VOC, temp, humidity, pressure) |
| `2950` | WAVE_RADON | Wave Radon Gen 2 |
| `3210` | WAVE_ENHANCE_EU | Wave Enhance (EU) |
| `3220` | WAVE_ENHANCE_US | Wave Enhance (US) |
| `3250` | CORENTIUM_HOME_2 | Corentium Home 2 |

### Service UUIDs (advertised, model-specific)

| Model | Service UUID |
|-------|-------------|
| Wave Plus | `b42e1c08-ade7-11e4-89d3-123b93f75cba` |
| Wave Mini | `b42e3882-ade7-11e4-89d3-123b93f75cba` |
| Wave Radon Gen 2 | `b42e4a8e-ade7-11e4-89d3-123b93f75cba` |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Serial number | mfr_data[0:4] | uint32 LE, matches label on device |
| Model | Derived from serial prefix | 7 known models |
| Model (alt) | Service UUID | If advertised |

### What Requires GATT Connection

- Radon level (Bq/m³)
- CO2 (ppm)
- VOC (ppb)
- Temperature (°C)
- Humidity (%)
- Atmospheric pressure (hPa)
- Ambient light
- Battery level

### Per apk-ble-hunting `airthings-app-android_passive.md`

Static analysis of the official Airthings app (`com.airthings.app.android`,
2026-10-22) adds the following. Only what the report states is recorded here.

**Contradictions / differences with the sections above (not resolved):**

- **Manufacturer data.** Report says: the app contains **no**
  `getManufacturerSpecificData` / `getServiceData` / `ScanRecord.getManufacturerData`
  calls and "reporting a company ID / byte layout would be a fabrication".
  Doc previously said (from `airthings-ble` / ESPHome): CID `0x0334` carries
  the serial as uint32 LE, and `src/adwatch/plugins/airthings.py` matches on
  that CID. The two are not strictly contradictory — the report only proves
  the *app* ignores manufacturer data, not that devices don't emit it — but
  the report's "no company ID" wording should not be read as overriding the
  library-sourced layout. A live capture of a Wave would settle it.
- **Local name.** Report says the **device name is the 10-digit serial
  number** (e.g. `2930XXXXXX`), prefix → model. Doc previously listed only
  the Wave Gen 1 `AT#NNNNNN-2900Radon` pattern and said other models "may not
  have distinctive names".
- **Model families.** Report maps `2900`-series → "Wave Classic" family
  (doc: "Wave Gen 1"), `2950` → "newer units" (doc: Wave Radon Gen 2).

**Additional advertised/proprietary service UUIDs** (report §Scanner notes;
usable as optional filters):

| Model | Service UUID |
|-------|-------------|
| Wave Classic (Gen 1) | `b42e1f6e-ade7-11e4-89d3-123b93f75cba` (new to this doc) |
| Wave Plus | `b42e1c08-…` (already listed) |
| Wave Gen 2 | `b42e4a8e-…` (already listed) |
| Wave Mini | `b42e3882-…` (already listed) |
| Newer "Atom" models | `b42e90a2-…` (new to this doc; full suffix not given in the report, presumed same base) |

**GATT (post-connect) reading characteristics** — `LATEST_VALUES`:
`b42e2a68` (Plus), `b42e4dcc` (Gen 2), `b42e3b98` (Mini); Wave Classic uses
discrete radon/temp/humidity characteristics. Full map in
`reports/airthings-app-android.md`.

**Privacy (report):** the serial-as-name is a static, per-device identifier
broadcast in the clear, so a unit (and household) is trackable regardless of
MAC randomisation. No sensor telemetry (radon etc.) leaks in the advert.

**Plugin gap:** `airthings.py` matches only CID `0x0334`. It does not match a
10-digit numeric local name or the `b42e…` service UUIDs. A future change
could add name-based matching (10-digit name with a known model prefix) and
service-UUID matching so Waves that advertise the serial only in the name are
still detected. Report code citations: `defpackage/yg.java` (per-model GATT
maps), `defpackage/xp3.java` (serial decode).

## Identity Hashing

```
identifier = SHA256("{mac}:{serial_number}")[:16]
```

## Detection Significance

- Very popular post-COVID for indoor air quality monitoring
- Presence detection identifies households with air quality concerns
- Serial number allows tracking specific devices
- Model identification reveals sensor capabilities (radon, CO2, etc.)

## References

- [airthings-ble](https://github.com/Airthings/airthings-ble) — Official Python library
- [ESPHome Airthings BLE](https://esphome.io/components/sensor/airthings_ble/) — Passive listener reference
- [wave-reader](https://github.com/Airthings/wave-reader) — Official Wave reader
- [waveplus-reader](https://github.com/Airthings/waveplus-reader) — Official Wave Plus reader
- apk-ble-hunting `reports/airthings-app-android_passive.md` — official-app static analysis (2026-10-22)
