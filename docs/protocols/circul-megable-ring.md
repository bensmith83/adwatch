# CIRCUL / CIRCUL Pro Ring (BodiMetrics, MegaBle SDK)

## Overview

The **CIRCUL** SpO2 / pulse-oximeter smart ring (BodiMetrics; app
`com.circul.zg29`, internal OEM namespace `com.zhaoguan`, v1.6.6.506) uses the
vendor **MegaBle** SDK (`io.mega.megablelib`) over the Nordic Android BLE
library. Sibling Mega rings advertise as `MR+` / `MRing+`.

Not to be confused with **Circular Ring 2** (`xyz.circular.circular`,
Circularing) — see [circular-ring.md](circular-ring.md). Both use "CR"-style
names (`CR39` here; Circular's Go label format `CR%04s%02dL…`), so name alone
needs care.

The live scan path consumes only **MAC + a 6-byte serial** from a
manufacturer-specific AD — both static, both broadcast in cleartext. The SDK
also ships two richer advert decoders (live pulse rate / SpO2 / battery) that
**this app does not wire in**; whether CIRCUL firmware emits those variants is
**unverified** (no live capture).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | exact `CR39` (CIRCUL); `MR+`, `MRing+` (sibling Mega rings, normalised to `MRing+`) | `ScanFilter` exact-name list + callback hashCode switch (`BleScanBinder.java:84-104,149`; `BleManage.java:2066`) |
| Manufacturer AD "company ID" | bytes `02 02` → `0x0202` (palindromic, so endianness is moot) | gate for the live layout. adwatch's SIG table assigns `0x0202` to **Rigado LLC**; the report judges it a vendor-chosen format tag, not a MegaHealth/BodiMetrics allocation — **misattribution trap** |
| Scan record length | 62 bytes expected by `parseV4` | i.e. adv + scan response |
| Service UUID / service data | none on any scan path | contrast the service-data ring fleets (`moyoung-ring`, `app-cq-ring` `0xFEE7`) |

### Manufacturer data — live layout (`MegaAdvParse.parseV4`)

Offsets relative to the AD-type byte `0xFF` (= T). Mfr-value offset = T−1.

| Offset (from T) | Mfr-value offset | Field | Size | Decode |
|-----------------|------------------|-------|------|--------|
| T+0 | — | AD type `0xFF` | 1 | first `0xFF` AD in the record |
| T+1..T+2 | 0–1 | company-ID field | 2 | must be `02 02` |
| T+3..T+8 | 2–7 | **BD_ADDR** | 6 | ring's public MAC, **reversed** (display `[+8]:[+7]:…:[+3]`) |
| T+9..T+14 | 8–13 | **Serial number** | 6 | raw → `UtilsBle.parseSnEnter`; scheme (V0/V1/V2/V3/ZG29V3) chosen by top 3 bits of the first two bytes |

Nothing else is consumed on the live path (`MegaAdvParse.java:115-181`).

### Manufacturer data — latent SDK layout `MegaAdvOnly` ("protocol 1")

Reached via `parseV3` when the byte after the `0xFF` type == `0x01`
(i.e. the non-`02 02` branch); `parseV4` discards the telemetry. Offsets
relative to the manufacturer AD's **length byte** (`index`):

| Offset | Field |
|--------|-------|
| index+2 | protocol (== 1) |
| index+3 / +4 / +5 | id / version / session |
| index+12..17 | serial (6 B) |
| index+18 | mode |
| index+19 | power |
| index+20 | batteryStatus |
| index+21 | **pr** (pulse rate) |
| index+22 | **spo2** |
| index+23 | stage (sleep/activity) |
| index+24 | gesture |

### Latent SDK layout `MegaAdvV2` ("MRingV2") — zero callers in the APK

Absolute offsets into the 62-byte scan record, gated by ASCII `MRingV2`
(`4D 52 69 6E 67 56 32`) at 53–59: battery @34, ringSize @35, serial @42–47,
isMonitoring @48 (`==1`), mode @49.

### What We Can Parse from Advertisements

| Field | Source | Confidence |
|-------|--------|------------|
| Ring MAC (embedded) | live layout | HIGH |
| 6-byte serial | live layout | HIGH |
| Model family | name (`CR39` vs `MRing+`) | HIGH |
| Pulse rate, SpO2, battery, mode, stage | `MegaAdvOnly` if emitted | **unverified for CIRCUL firmware** |
| Battery, ring size, monitoring state | `MegaAdvV2` if emitted | **unverified / dead code** |

### What Requires GATT

SpO2 / HR / ECG / BP streams over the `F86AFEE2…` service (plaintext,
static-key bind) — connection-only; see apk-ble-hunting `reports/circul-zg29.md`.

## Identity Hashing

```
identifier = SHA256("circul:" + serial_6B_hex)[:16]
```

The in-payload serial (and embedded MAC) is stable per ring and would defeat
link-layer address randomization.

## Detection Significance

- **Permanent tracking ID in every advert** — cleartext serial + public MAC
  on a medical-adjacent, worn-overnight device.
- **Device class disclosed** by `CR39` / `MRing+` name + `02 02` tag.
- **Potential live-biometric leak** (SpO2 / pulse) if the firmware broadcasts
  the `MegaAdvOnly` variant — needs a capture.
- Continuous overnight presence → occupancy signal.

## Plugin gaps

No adwatch plugin matches. A future parser would match name `^(CR39|MR\+|MRing\+)$`
+ manufacturer CID `0x0202` with ≥ 12-byte value, extract MAC (reversed) +
serial; opportunistically try `MegaAdvOnly` (first value byte `0x01`) and the
`MRingV2` tag. It must not treat bare CID `0x0202` as CIRCUL (Rigado's
registered ID) — require the name.

## References

- apk-ble-hunting `reports/circul-zg29_passive.md` (`io/mega/megablelib/MegaAdvParse.java:26-28,55,91-102,115-181`; `MegaAdvOnly.java:29-47`; `service/BleScanBinder.java:66,84-104,149-157`; `com/zhaoguan/common/ble/BleManage.java:2066-2085`; `UtilsBle.java:399-407`)
- apk-ble-hunting `reports/circul-zg29.md` (GATT)
- adwatch `src/adwatch/_bt_company_ids.py` (`0x0202: Rigado LLC`)
