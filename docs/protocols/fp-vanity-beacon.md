# "FP" Vanity-Forged Beacon Plugin (CID 0x5046)

## Overview

This parser flags a small but interesting BLE family: **devices advertising under a Bluetooth SIG company identifier that the SIG has not assigned to anyone**. The wire prefix `46 50` decodes as little-endian SIG company ID `0x5046` — except `0x5046` is *not* in the SIG's [company-identifiers registry](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) (the registry tops out at `0x10C4` as of early 2026) and is also absent from [Nordic's bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database).

The bytes were chosen because they spell ASCII `"FP"` — the vendor's initials baked into the SIG slot. This is non-compliant with the Bluetooth spec (vendors are supposed to license a real ID from the SIG) but works on any scanner that doesn't validate against the registry. From a fingerprinting perspective, it's a feature: anyone using `0x5046` is almost certainly a single private integrator.

The first four payload bytes are an ASCII model code — `FPBO` (heartbeat-only asset tag) or `FPBG` (sensor-equipped tag). Bytes 9..12 of the manufacturer data are a **printable-BCD commissioning date** that reads literally as `2021-10-14` / `2023-05-05` — the vendor chose BCD digits so the date is legible in a hex dump, matching the same readability ethos that produced the vanity SIG ID.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x5046` | NOT SIG-assigned. Bytes spell ASCII `"FP"`. |
| Model code (ASCII) | `"FPBO"` or `"FPBG"` | First 4 bytes of mfg data (CID's "FP" + payload's first 2 bytes). |
| Commission date | printable BCD at offsets 9..12 of mfg data | E.g. `20 21 10 14` → `2021-10-14`. |

### Manufacturer Data Layout

| Offset | FPBO (28 B) | FPBG (27 B) | Field |
|---|---|---|---|
| 0..1 | `46 50` | `46 50` | Forged SIG CID ("FP") |
| 2..3 | `42 4F` ("BO") | `42 47` ("BG") | ASCII model variant |
| 4..8 | `21 09 15 47 11` | `23 05 59 17 12` | BCD timestamp / serial (low confidence) |
| 9..12 | `20 21 10 14` | `20 23 05 05` | **Commissioning date** — printable BCD `YYYYMMDD` |
| 13 | `59` / `5A` / `5B` (varies) | `98` (constant) | FPBO: heartbeat sequence counter / FPBG: status flag |
| 14..15 | `FF FF` | `00 C7` | End-of-fixed-block sentinel / sensor reading |
| 16..17 | `08 00` | `05 A1` | const `0x0008` / second sensor reading (1441) |
| 18..26 | zero pad | bit-flag, sentinel, rolling token | telemetry tail |

### Model Variants

- **FPBO** — heartbeat beacon. Fixed commissioning stamp + ~1 Hz sequence counter + zero padding. Consistent with a passive asset-tracking tag.
- **FPBG** — sensor-equipped beacon. Two 16-bit fields (likely environmental readings: temperature, contact state, etc.) and a fast-varying tail byte. Consistent with a gateway / environmental monitor / door sensor.

## Detection Significance

- **Single-integrator private deployment.** No public hits across the SIG registry, FCC database, GitHub code search, or vendor catalogs means these are custom firmware on commodity hardware (nRF52 / ESP32) deployed by one integrator. Picking up multiple units in a 48 h window confirms a co-located fleet.
- **Vanity SIG ID is a fingerprint.** Once you know `0x5046` = "FP integrator", every future capture of that ID belongs to the same fleet. You can use this to track when the fleet moves between locations.

## Privacy Notes

- The commissioning date in the payload is a per-device install marker — if you co-locate multiple units, you can correlate their installation dates and infer the deployment timeline.
- Random MAC + no local name + no service UUIDs = the vendor explicitly chose minimum-disclosure broadcasting. The deployment owner is privacy-conscious.

## What We Cannot Parse from Advertisements

- The vendor identity. Without a brand name or service UUID, we don't know which company "FP" is. Best path forward is physical: photograph a unit at close range and OCR the case label.
- The semantics of FPBG's two 16-bit sensor fields (`0x00C7` = 199 and `0x05A1` = 1441 in our samples). We surface them as `payload_hex` but don't claim to decode them.

## References

- [Bluetooth SIG company identifiers (canonical YAML)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — verified `0x5046` is absent.
- [Nordic Semiconductor bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — verified absent in 4,016-entry mirror.
- [Requesting Assigned Numbers — Bluetooth SIG](https://support.bluetooth.com/hc/en-us/articles/360062030092-Requesting-Assigned-Numbers) (explains the legitimate allocation process this vendor bypassed).
