# Owned E-Scooters & E-Bikes (Dualtron/Minimotors, NAVEE, Unagi, Pure & Hiboy (ZYD), Aventon, OKAI)

## Overview

Consumer e-scooters and e-bikes are **connect-and-control** BLE peripherals:
speed, battery/BMS, lock state, ride modes and passwords all live behind GATT.
None of the apps analysed below parse manufacturer- or service-data telemetry
from advertisements. What a passive scanner gets is a **discovery signature**
(name token or service UUID), the MAC, RSSI and — for NAVEE — a product ID.
Expect low beacon yield while a vehicle is parked / powered off.

Seven apps from apk-ble-hunting batches 26–28 are covered; they are separate
vendors except Pure and Hiboy S2, which share the ZYD / HobbyWing stack.

| Vendor / app | Package | Passive signature | Confidence |
|--------------|---------|-------------------|------------|
| Minimotors (Dualtron, Rovoron) | `com.minimotors.escooter` | name contains `DUALTRON` / `mini` / (`BLE` and `Device`) | HIGH (but loose) |
| NAVEE / uCaret (+ Ld, Exo, Dg partner families) | `com.navee.ucaret` | name contains `NAVEE`; Ld: UUID `C8747810-4B8E-11F1-AB07-0002A5D5C51B` | HIGH |
| Unagi Model One | `com.unagiscooters.one` | service UUID `0xFFF0` (generic HM-10) + any name | HIGH (but generic) |
| Pure Electric (ZYD) | `com.zydtech.Pure` | name prefix `ZYD` / `ZYD_` (case-insensitive) | HIGH |
| Hiboy S2 (ZYD) | `com.zydtech.hiboys2` | name prefix `hw_z` / `zyd` (case-insensitive) | HIGH |
| Aventon e-bike display (Ditai) | `com.ditai.aventon` | service UUIDs `0xFFE0`/`0xFFE5`/`0xFFF0`/`0xFFB0` (generic) | HIGH mechanism / MEDIUM per-model |
| OKAI scooter platform (many white-label / fleet) | `com.yele.app.bleoverseascontrol` | service UUID `669A0C20-0008-A7BA-E311-0685C0F7978A` | HIGH (vendor-unique) |

No company IDs are involved for any of these.

## BLE Advertisement Format

### Identification

| Vendor | Signal | Value | Notes |
|--------|--------|-------|-------|
| OKAI | 128-bit service UUID | `669A0C20-0008-A7BA-E311-0685C0F7978A` | best match key in this doc — vendor-unique. Present when powered on. |
| OKAI | 16-bit service UUID | `0xFE59` | Nordic Secure/Buttonless DFU — a unit mid-OTA advertises this *instead*; generic, see [nordic-dfu.md](nordic-dfu.md) |
| NAVEE | local name | contains `NAVEE` | then PID + MAC parsed from scan record |
| NAVEE / Ld e-bike | 128-bit service UUID | `C8747810-4B8E-11F1-AB07-0002A5D5C51B` | FastBle scan filter |
| NAVEE / Exo scooter | PID in advert | — | matched by product ID; service UUID `0xFFF0` family (GATT) |
| NAVEE / Dg ("Digitech") e-bike | PID in advert | — | matched by product ID; service UUIDs `0xFFE0`/`0xFFE5` family (GATT) |
| Pure (ZYD) | local name | `^ZYD` / `^ZYD_` (ci); model substring e.g. `ZYD012_L12E` | |
| Hiboy S2 (ZYD) | local name | `^hw_z` / `^zyd` (ci) | `hw_z` = HobbyWing |
| Minimotors | local name | contains `DUALTRON`, or contains `mini`, or contains both `BLE` and `Device`, or starts with a server-supplied factory abbreviation | no fixed prefix (`DEVICE_NAME_PRE = ""`) |
| Unagi | service UUID | `0xFFF0` (OS `ScanFilter`) | generic HM-10/TI serial-module UUID — **not unique**; name required non-null but no pattern enforced (HM-10 default often `HMSoft`) |
| Aventon | service UUIDs | any of `0xFFE5`, `0xFFE0`, `0xFFF0`, `0xFFB0` | shipping defaults; server record can override per bike. `FFE0`/`FFE5` are generic HM-10 UUIDs |

Note the ZYD pair: Hiboy's `zyd` prefix (ci) also matches Pure's `ZYD`
prefix — a name match alone can't distinguish them; `hw_z` is Hiboy-only.

### NAVEE product ID (PID)

NAVEE is the one vendor with a passive datum beyond identity: the app parses a
**product ID** (vehicle model) and MAC out of `getScanRecord()` before
connecting (`BleHandler.s()/r()`, `BleHandler.java:1097,1130`); the Exo and Dg
scan strategies discover by PID too. **The byte offset of the PID within the
record was not traced** (report confidence MEDIUM, per-family parse) — a
future parser needs a live capture to place it.

### What We Can Parse from Advertisements

| Field | Source | Vendors |
|-------|--------|---------|
| Vendor / platform | UUID or name token | all |
| Model hint | name substring (`ZYD012_L12E`), PID (NAVEE), factory abbreviation (Minimotors) | Pure, NAVEE, Minimotors |
| Presence + MAC | radio | all |
| DFU-mode flag | `0xFE59` present | OKAI |

### What Requires GATT

| Vendor | GATT surface (reference only) |
|--------|-------------------------------|
| Minimotors | Telink serial `0xFE60` (write `FE61`, notify `FE62`, OTA `FE63`); 16-byte `AA…EE` frames with a weak per-byte scramble; default PIN `199977` |
| NAVEE | `0xD0FF` (notify `B003`, write `B002`), frame `55 AA 00 31 <len> … <cksum> FE FD` (plaintext, despite "encryptData" log); Ld `C8747810/14/11`; Dg `FFE0/FFE4` + `FFE5/FFE9`; Exo `FFF0/FFF1/FFF2` |
| Unagi | 25-byte status frame on notify `0xFFF2` (write `FFF1`); AT channel `0xF2F0` with weak nibble cipher; TI OAD `F000FFC0`; DIS serial `2A25` |
| Pure / Hiboy (ZYD) | DATA `0xF1F0` (notify `F1F2`, write `F1F1`), CMD/AT `0xF2F0` (notify `F2F2`, write `F2F1`), CRC16 framing, `AT+PWD[…]` auth; Pure also a hardcoded-HMAC unlock key |
| Aventon | write svc `FFE5`/char `FFE9`, notify svc `FFE0`/char `FFE4`; versioned protocol with optional `5A 5A` header |
| OKAI | GATT service `0x2C00` (write `2C01`, notify `2C03`); ASCII `GT*`/`QT*` commands (`GTINF`, `QTQSN`) give model/serial |

Speed, odometer, battery/BMS, lock state — all GATT-only for every vendor.

## Identity Hashing

No payload-stable identifier is broadcast (except possibly NAVEE's PID, which is
a model ID, not a unit ID). None of the reports found RPA handling, and the
Unagi report notes TI/HM-10 modules commonly use a static public address, so:

```
identifier = SHA256("<vendor>:" + mac)[:16]
```

## Detection Significance

- **Theft targeting.** `DUALTRON`, `NAVEE`, `ZYD…`, and OKAI's UUID announce a
  relatively high-value vehicle whenever it is powered and advertising.
- **Owner tracking by MAC** across locations / commute patterns (no rotation
  evidence for any vendor).
- **Pure's `setAdvParams`** lets the app reconfigure the scooter's own
  advertisement — a given unit's advert name/payload can vary (Hiboy shares the
  capability).
- No live telemetry leaks passively; the weak GATT protections (scrambles,
  default PINs, plaintext AT passwords) are an *active* exposure.

## Plugin gaps

No adwatch plugin matches any of these today. Strongest candidates:

1. **OKAI** — match service UUID `669A0C20-0008-A7BA-E311-0685C0F7978A`
   (vendor-unique; presence + MAC).
2. **NAVEE** — name contains `NAVEE`; Ld e-bike UUID `C8747810-4B8E-11F1-AB07-0002A5D5C51B`.
   PID extraction blocked on a live capture.
3. **ZYD** — name `^(ZYD|hw_z)` (ci); emit `brand` Pure vs Hiboy only when
   unambiguous.
4. **Minimotors** — `DUALTRON` substring is safe; `mini` and `BLE…Device` are
   far too loose for a passive matcher (would hit unrelated devices) — use
   `DUALTRON` only.
5. **Unagi / Aventon** — not passively distinguishable: `FFF0`/`FFE0`/`FFE5`
   are generic HM-10 UUIDs (adwatch's `arccos_golf.py` already gates hard on
   `0xFFF0` for this reason). No plugin recommended without a name capture.

## References

- apk-ble-hunting `reports/minimotors-escooter_passive.md` (`Ey4DeviceSearchActivity.java:1250-1260`; `BlueService.java:39`; `MyDeviceManager.java:229,282`)
- apk-ble-hunting `reports/navee-ucaret_passive.md` (`ble/scan/NaveeScanStrategy.java:41`; `BleHandler.java:1083,1097,1130`; `ble/port/LdEBikeDevicePort.java:203`)
- apk-ble-hunting `reports/unagiscooters-one_passive.md` (`ScootersFragment.java:146-168,678-679`; `MainActivity.java:343-389`)
- apk-ble-hunting `reports/zydtech-pure_passive.md` (`MainActivity$coreListener$1.java:212`; `SettingsFragment.java:381,800,803`; `BleCore.java:84,2105-2109,3015`; `PinKt.java:10`)
- apk-ble-hunting `reports/zydtech-hiboys2_passive.md` (`DialogManager.java:181`; `BleCore.java:2095-2099,3001`; `Constant.java:46-54`)
- apk-ble-hunting `reports/ditai-aventon_passive.md` (`defpackage/hj2.java:66,88-105`; `o42.java:58-85`)
- apk-ble-hunting `reports/yele-app-bleoverseascontrol_passive.md` (Blutter: `asm/equipment/equipment_manager.dart` @0x843664)
