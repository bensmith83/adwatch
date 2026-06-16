# Scent Tech smart aroma diffuser (white-label)

## Overview

A smart aroma/scent diffuser running the **"Scent Tech"** companion-app
platform. Observed in the 2026-06-15 NearSight sweep (2 devices, 138
sightings, 2026-06-13) advertising a tiny static manufacturer-data frame and a
`Scent-<hex>` local name.

## Vendor attribution

**Platform = HIGH; specific retail brand = UNKNOWN (white-label).**

- The `Scent-<hex>` BLE local-name convention is documented in the **Scent
  Tech app operation manual** (a connected diffuser appears as
  `Scent-B501F0…` — same shape as the captured `Scent-A199DD` /
  `Scent-4153FB`).
- Companion app: **Scent Tech** — iOS App Store id `1662466433` / Android
  `com.yooai.scentlife`, published by **Guangdong Grasse Environmental
  Technology Co.** (Grasse Aroma). Grasse's own guide confirms the diffusers
  pair over Bluetooth, located by device name.
- The platform is white-labeled across many resellers (sold variously as
  "Smart Scent Air Machine" etc.), so the badge on any individual unit is not
  recoverable from the advertisement.

The company-ID bytes `0x5353` are ASCII **"SS"** — a vanity/forged company ID,
**not** SIG-registered. Read as "Smart Scent" (the platform's repeated
self-branding); recorded raw as well. The payload `B00000` is a static model
marker (consistent with the "B"-class device identifier in the confirmed app
screenshot).

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x5353` (ASCII "SS", vanity/forged) |
| Manufacturer payload | ASCII `"B00000"` (static model marker) |
| Local name | `^Scent-[0-9A-Fa-f]{6}$` (e.g. `Scent-A199DD`) |
| Address type | random |

`mfg = 5353423030303030` → `53 53` ("SS") + `42 30 30 30 30 30` ("B00000").

Match if **either** the strict `Scent-<6hex>` name matches **or** company ID
`0x5353` carries a printable-ASCII payload (the ASCII guard rejects unrelated
0x5353 "SS" squatters emitting binary payloads).

## Parser scope

Passive decode only. Surface `vendor` (platform), `companion_app`,
`company_id_ascii` ("SS"), `model_marker` (the ASCII payload), and `device_id`
(the 6 hex from the name). Stable key `scent_tech_diffuser:<device-id-or-MAC>`.

## Confidence

- Platform: **high** (app + manual confirm the `Scent-<hex>` name shape).
- Retail brand: **unknown** (white-label). No vendor brand claimed.

## References

- Scent Tech app — https://apps.apple.com/us/app/scent-tech/id1662466433
  (Android `com.yooai.scentlife`).
- NearSight app: `Sources/Parsers/ScentTechDiffuserParser.swift`,
  `research/sweep-2026-06-15-candidates.md`.
