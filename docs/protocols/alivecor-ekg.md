# AliveCor Kardia ECG Plugin

> **⚠️ Correction (2026-08-17).** Earlier revisions of this doc identified
> AliveCor devices by the local name `EKG-*` and the service UUID
> `021a9004-0382-4aea-bff4-6b3f1c5adfb4`. Both were wrong: that UUID is the
> Espressif BLE Wi-Fi-provisioning service, and the only `EKG-` unit ever
> observed (`EKG-99-23-4c`) is a Fellow "EKG" smart kettle in setup mode —
> see [fellow.md](fellow.md) and the retracted [medical-ekg.md](medical-ekg.md).
> The identification below is the corrected, Kardia-only one (from the
> decompiled Kardia app, apk-ble-hunting `alivecor-kardia_passive.md`).
> Parsers: adwatch `alivecor_ekg.py` v1.2.0, NearSight `AliveCorParser` v2.

## Overview

AliveCor Kardia is a family of personal ECG monitors (KardiaMobile,
KardiaMobile 6L, KardiaCard) that pair with a smartphone via BLE. The
modern products advertise per-product 128-bit service UUIDs and a
recognisable device-name prefix. Presence of the UUID alone is a
PHI-by-inference signal (an FDA-cleared 6-lead ECG is nearby).

## BLE Advertisement Format

### Identification

| Product | Service UUID | Local name |
|---------|--------------|------------|
| KardiaMobile 6L | `ac060001-328c-a28f-9846-5a8aa212661b` | `KardiaMobile_6L_<serial>` |
| KardiaCard | `ac010001-328c-a28f-9846-5a8aa212661b` | `KardiaCard_<serial>` |
| older KardiaMobile | (none known) | `KardiaMobile[_<suffix>]` |

Match strategy: either Kardia UUID, or a name matching
`^(KardiaMobile_6L|KardiaCard|KardiaMobile)(?:[_-](.+))?$`. A **present**
non-Kardia name is never claimed, even alongside a Kardia UUID (name-gate
safety for telemetry redaction — same rule as Nespresso). UUID-only
sightings with no name still parse.

Not identification signals (retracted): `^EKG-` names, `021a9004-…`
(Espressif provisioning), `7aebf330-…` (Fellow aux UUID).

### Advertisement Data

- No manufacturer data observed
- No service data observed

### Parser Scope (Passive Only)

| Field | Source | Notes |
|-------|--------|-------|
| `product_family` | UUID or name token | `KardiaMobile 6L` / `KardiaCard` / `KardiaMobile` |
| `device_id` | name suffix after `_`/`-` | unit serial; keys identity across MAC rotation |
| `match_basis` | — | `name`, `kardia_6l_uuid`, `kardia_card_uuid`, `+`-joined |

Actual ECG readings require an active GATT connection via the Kardia app.

## Identity Hashing

```
identifier = SHA256("alivecor_ekg:<device_id>")[:16]   # name carries the serial
identifier = SHA256("<mac>:alivecor_ekg")[:16]         # UUID-only sighting
```

## Observed in DB

No genuine Kardia unit has been captured in the corpus yet; the sightings
previously listed here (`EKG-99-23-4c`, 959k+) belong to
[fellow.md](fellow.md).

## References

- [AliveCor KardiaMobile](https://www.alivecor.com/)
- apk-ble-hunting `alivecor-kardia_passive.md`
- [Kardia BLE analysis](https://github.com/nicpottier/kardia-python)
