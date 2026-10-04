# Fellow "EKG" Smart Kettles (Stagg EKG / EKG+ / EKG Pro, Corvo EKG)

## Overview

Fellow's connected kettles are ESP32-based and advertise over BLE for pairing
with the Fellow app. Two advertisement shapes are known:

1. **Model-name advertisement** (from the decompiled Fellow app,
   apk-ble-hunting `fellowapp_passive.md`): a custom 128-bit primary service
   UUID, an aux UUID in some frames, and a local name carrying the model and
   often an ESP32 MAC-suffix tail (`Stagg EKG Pro-A1B2`).
2. **`EKG-<hex tail>` setup beacon** (field capture): local name
   `EKG-XX-XX-XX` plus the Espressif BLE Wi-Fi-provisioning service UUID
   `021a9004-0382-4aea-bff4-6b3f1c5adfb4`. This is the kettle in
   pair / provisioning mode.

> **⚠️ Attribution note (2026-08-17).** Shape 2 was documented for a long time
> as a "medical EKG monitor" ([medical-ekg.md](medical-ekg.md), now retracted)
> and routed to the AliveCor plugin ([alivecor-ekg.md](alivecor-ekg.md)). That
> was a guess from the "EKG" token. Why it is Fellow:
>
> * Fellow's kettle line is literally named **EKG** ("Electric Kettle
>   Gooseneck"): Stagg EKG, Stagg EKG+, Stagg EKG Pro, Corvo EKG.
> * The only unit ever observed (`EKG-99-23-4c`, 959k+ sightings) advertised
>   **only** the Espressif provisioning UUID — Fellow's kettles are ESP32;
>   AliveCor's Kardia devices are not.
> * The old medical-ekg doc listed a second "EKG" UUID,
>   `7aebf330-6cb1-46e4-b23b-7cc2262c605e` — that is Fellow's **aux** service
>   UUID from the decompiled Fellow app.
> * Genuine AliveCor Kardia hardware advertises `ac060001-…`/`ac010001-…` with
>   `KardiaMobile_*`/`KardiaCard_*` names — never `EKG-`.
>
> Confidence: high on the "not AliveCor" half; high-but-not-yet-proven on the
> Fellow half — no capture has yet shown an `EKG-` name together with a
> Fellow-unique UUID (the two UUIDs were listed against the same names in the
> original doc, but that pairing was never re-observed in the corpus). If a
> capture ever pairs `EKG-…` with `2291c4b6-…`/`7aebf330-…`, this closes;
> if it pairs with some other vendor UUID, revisit.

## BLE Advertisement Format

### Identification

| Signal | Value | Role |
|--------|-------|------|
| Primary service UUID | `2291c4b6-5d7f-4477-a88b-b266edb97142` | vendor-unique, match key |
| Aux service UUID | `7aebf330-6cb1-46e4-b23b-7cc2262c605e` | vendor-unique (OTA / provisioning), match key |
| Local name (model) | `^(Stagg EKG Pro\|Corvo EKG\|Fellow EKG Pro)(-[0-9A-Fa-f]{2,8})?$` | match key; tail = ESP32 MAC suffix |
| Local name (setup beacon) | `^EKG-[0-9A-Fa-f]{2}(-[0-9A-Fa-f]{2})+$` (e.g. `EKG-99-23-4c`) | match key; tail = per-unit id |
| Espressif provisioning UUID | `021a9004-0382-4aea-bff4-6b3f1c5adfb4` | **corroboration only** — never a match key (it is a platform UUID owned by the `espressif_prov` parser); surfaced as `provisioning_mode` |

Match strategy: any one of primary UUID / aux UUID / model name / `EKG-` tail
name. A **present** local name that is not a Fellow token is always rejected,
even alongside a Fellow UUID (keeps the parser safe as a name-gated parser
for telemetry redaction — same rule as Nespresso).

- No manufacturer data observed
- No service data observed

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| `model` | model local name | Stagg EKG Pro / Corvo EKG / Fellow EKG Pro |
| `mac_suffix` | model-name tail | ESP32 MAC suffix, per-unit, survives MAC rotation |
| `device_id` | `EKG-` tail | per-unit id baked into the GAP name, survives MAC rotation |
| `model_hint` | `EKG-` path | "Stagg EKG / Corvo EKG (setup beacon)" — exact model unknown from this shape |
| `provisioning_mode` | Espressif prov UUID present | kettle is in pair / setup mode (may be leaking Wi-Fi credentials over BLE) |
| `aux_service_seen` | aux UUID present | |
| `match_basis` | — | which of the signals fired, `+`-joined (e.g. `name_ekg_tail+espressif_prov_uuid`) |

### What We Cannot Parse (requires GATT)

- Temperature setpoint / current temperature, hold state
- Wi-Fi SSID / firmware version

## Identity Hashing

```
identifier = SHA256("fellow:<mac_suffix | EKG tail>")[:16]   # when a per-unit id is present
identifier = SHA256("fellow:<mac>")[:16]                      # UUID-only sightings
```

Both name-embedded ids are stable across BLE MAC rotation, so a kettle keeps
one identity while advertising from random addresses.

## Observed in DB

- Local name `EKG-99-23-4c`, service UUID `021A9004-0382-4AEA-BFF4-6B3F1C5ADFB4`,
  no manufacturer data, no service data, random address — one unit, 959k+
  sightings (a very active advertiser: it never left provisioning mode).

## Parser Scope (Passive Only)

- adwatch: `src/adwatch/plugins/fellow.py` (v1.1.0 adds the `EKG-` path;
  `alivecor_ekg.py` v1.2.0 dropped it)
- NearSight: `FellowKettleParser` (`fellow`); `AliveCorParser` v2 is
  Kardia-only. Both parsers record `match_basis`.

## References

- apk-ble-hunting `fellowapp_passive.md` (primary/aux UUIDs, model names)
- Espressif BLE provisioning service UUID: ESP-IDF `wifi_provisioning`
  (`021a9004-0382-4aea-bff4-6b3f1c5adfb4`)
- [Fellow Stagg EKG](https://fellowproducts.com/products/stagg-ekg-electric-pour-over-kettle)
