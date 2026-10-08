# Google Nest

## Overview

Google Nest devices (thermostats, cameras, speakers, displays, doorbells) broadcast BLE advertisements using service UUID `0xFEAF` (assigned to Nest Labs Inc.). This enables device setup via the Google Home app and local device discovery.

## BLE Advertisement Format

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFEAF` | Nest Labs Inc. (Bluetooth SIG member UUID). OpenWeave advertises its WoBLE service data under it |
| Service data | Weave BLE service-data block | Layout below |
| Local name | `N` + 4 characters | Opaque per-unit "device code". It is not a Weave pairing code (see below) |

### Service data: Weave BLE service-data blocks

The FEAF service data is one Weave BLE service-data block. Byte 0 is the
block length, counting every byte after itself. Byte 1 is the block type.
OpenWeave (`src/ble/WeaveBleServiceData.h`) defines two types: `0x01` device
identification and `0x02` token identification.

#### Block type 0x01: `WeaveBLEDeviceIdentificationInfo` (17 bytes)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 1 | BlockLen | `0x10` (16 bytes follow) |
| 1 | 1 | BlockType | `0x01` |
| 2 | 1 | MajorVersion | `0` in every capture |
| 3 | 1 | MinorVersion | `2` on Nest Labs and Google units. `1` on the one third-party vendor seen, which matches the openweave device layer's own `kMinorVersion = 1` |
| 4-5 | 2 | DeviceVendorId | uint16 LE. `0x235A` Nest Labs, `0xE100` Google, `0xE727` Yale (`src/lib/core/WeaveVendorIdentifiers.hpp`) |
| 6-7 | 2 | DeviceProductId | uint16 LE, scoped to the vendor |
| 8-15 | 8 | DeviceId | uint64 LE. The unit's Weave node id (`FabricState.LocalNodeId`), usually a vendor OUI followed by a serial. It is per unit and permanent: one corpus frame stayed byte-identical across 88 rotated BLE addresses |
| 16 | 1 | PairingStatus | `0` unpaired, `1` paired to a Nest service account (`IsPairedToAccount()` in the openweave device layer, which checks for a stored `PairedAccountId`). `2` also occurs and has no defined meaning |

Example (Nest Labs vendor, product `0x0017`, paired, device id zeroed):

```
10 01 00 02 5a 23 17 00  xx xx xx xx xx xx xx xx  01
^^ ^^ ^^ ^^ ^^^^^ ^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^  ^^
len  type  ver  vendor   product   device id (LE)      pairing
```

#### Block type 0x03 (20 bytes, BlockLen `0x13`)

OpenWeave does not define this type. In the corpus:

- Bytes 2-3 are fixed for a given advertiser.
- Byte 4 behaves like a counter.
- Bytes 5-6 take only a few values.
- Bytes 7-19 change on every frame.

The block is undecoded. It is 80% of the FEAF frames in the corpus (950
distinct frames, against 235 for type 0x01).

### Product ids

The only public product-id table is openweave's
`src/lib/profiles/vendor/nestlabs/device-description/NestProductIdentifiers.hpp`.
It covers the Nest Labs vendor and gives codenames, not retail names:

| Id | Codename | Retail product | Evidence |
|----|----------|----------------|----------|
| 0x0001-0x0004 | Diamond / Diamond2 (+ backplates) | — | codename only |
| 0x0005, 0x001E, 0x001F | Topaz (deprecated in the header in favour of the two Topaz1 ids) / Topaz1LinePowered / Topaz1BatteryPowered | Nest Protect (1st gen) | Google Help: Technical Info "Model: Topaz 1.x" = 1st gen. Not seen in corpus |
| 0x0006, 0x0007, 0x000F | Amber backplate / Amber Heat Link / Amber2 Heat Link | — | codename only |
| **0x0009** | **Topaz2** (deprecated in the header in favour of the two Topaz2 ids) | **Nest Protect (2nd gen)** | Google Help "How to tell which Nest Protect you have": Technical Info "Model: Topaz 2.x" = 2nd gen |
| **0x000A** | **Diamond3** | **Nest Learning Thermostat** (generation not publicly stated) | `diamond3` is a board in Nest's nest-learning-thermostat open-source release |
| 0x000B | Diamond3Backplate | — | |
| 0x000D, 0x0010-0x0012 | Quartz / SmokyQuartz / Quartz2 / BlackQuartz | — | codename only |
| 0x0014, 0x0015 | Onyx / OnyxBackplate | — | codename only |
| 0x0020, 0x0021 | Topaz2LinePowered / Topaz2BatteryPowered | Nest Protect (2nd gen) | same Google Help source. Not seen in corpus |

No public source maps Google (`0xE100`) product ids. NearSight shows those
as "Nest product 0x000C" rather than guessing.

Corpus (distinct type-0x01 frames, so roughly distinct units):

| Vendor | Product | Frames | PairingStatus seen |
|--------|---------|--------|--------------------|
| Google 0xE100 | 0x000C | 100 | 99×1, 1×0 |
| Google 0xE100 | 0x0008 | 38 | 34×1, 1×0, 3×2 |
| Google 0xE100 | 0x000F | 29 | 1 |
| Google 0xE100 | 0x0019 | 19 | 1 |
| Google 0xE100 | 0x0010 | 5 | 1 |
| Google 0xE100 | 0x0006 | 2 | 1 |
| Nest Labs 0x235A | 0x0009 (Nest Protect 2nd gen) | 13 | all 0 |
| Nest Labs 0x235A | 0x0017 | 8 | 6×1, 2×0 |
| Nest Labs 0x235A | 0x0016 | 5 | 1 |
| Nest Labs 0x235A | 0x000A (Nest Learning Thermostat) | 3 | all 0 |
| Nest Labs 0x235A | 0x0011 (Quartz2) | 2 | 1 |
| Nest Labs 0x235A | 0x0014 (Onyx) | 1 | 2 |
| unknown 0x131A | 0x0002 (block v0.1) | 10 | all 0 |

PairingStatus says whether the unit is paired to a Nest service account, so
it only means "set up" for Nest Labs and Google products. NearSight makes no
setup claim for any other vendor: all ten 0x131A units report `0`.

Every Nest Protect and Learning Thermostat in the corpus reports `0`, even
though they are installed alarms and thermostats. On those products the byte
does not track setup, so NearSight makes no setup claim for them. That covers
every Topaz id (1st and 2nd gen), including the ones not yet seen in the
corpus, and Diamond3. On every other Nest Labs or Google product, `1` is
shown as "Set up" and `0` as "Not set up yet".

### Local name ("device code")

- The name is always `N` followed by 4 characters. Across 53 corpus names,
  those 4 characters use 0-9 and A-Z without I and O, so Q and Z both occur.
- It is not a Weave pairing code. Those are 6 characters (9 for Kryptonite),
  use the Verhoeff-32 alphabet `0123456789ABCDEFGHJKLMNPRSTUVWXY` (no Q or Z),
  and end in a check character (`src/lib/support/pairing-code`).
- It is not the openweave device layer's default BLE name either. That name is
  `NEST-` followed by the low 16 bits of the node id in hex.
- It does not match any base-32, base-34 or base-36 rendering of the node id
  (full id, low 32 bits or low 40 bits, either digit order) across 27
  name+frame pairs.
- Treat it as an opaque per-unit code that survives address rotation.

## Identity

- `identifier = SHA256(mac_address)[:16]`. This is unchanged.
- The node id is deliberately not used as a cross-rotation identity key. It
  is an OUI plus a serial with roughly 24-40 unknown bits, so any hash of it
  that leaves the device can be brute-forced back to the id.

## Parser Match Paths (May 2026)

The Nest parser matches an advertisement under any of these conditions:

1. **Service data on `FEAF`** (either the short-form key `"FEAF"` that
   CoreBluetooth gives on iOS, or the long-form 128-bit expansion
   `0000FEAF-0000-1000-8000-00805F9B34FB`). When present, the
   service-data block is decoded as described under "Service data"
   above (block type, vendor id, product id, pairing status).

2. **FEAF in the advertised service-UUID list** + **local name matching
   a Nest device code** (`^[NR][0-9A-Z]{4}$`: `N` or `R` plus 4
   characters; see "Local name" above, this is not a Weave pairing
   code). This catches the common case where a mains-
   powered Nest device broadcasts only the FEAF UUID and its 5-char
   code, with no service data.

Match path #2 was added after observing ~4,000 sightings in adwatch
research exports where FEAF + N/R-prefix name were present but no
service data was attached — those captures would silently fail to
parse under the old serviceData-only logic.

## Known Products Using 0xFEAF

| Product | Notes |
|---------|-------|
| Nest Thermostat | All generations |
| Nest Cam / Dropcam | Indoor/outdoor cameras |
| Nest Hub / Hub Max | Smart displays |
| Nest Mini / Audio | Smart speakers |
| Nest Doorbell | Video doorbell |
| Nest Protect | Smoke/CO detector |
| Google Home (legacy) | Rebranded to Nest |

## Detection Significance

- Smart home infrastructure device
- Broadcasts continuously (always-on BLE for Google Home app control)
- Common in residential environments
- Multiple Nest devices at one location is typical

## Future Work

- Map Google (0xE100) product ids. This needs captures from known devices,
  for example from a Google Home app device list next to a scan.
- Work out block type 0x03. The fixed bytes 2-3 might be a short per-unit
  or per-home tag.
- Find out what PairingStatus `2` means.

## References

- [Bluetooth SIG — Service UUID 0xFEAF](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Nest Labs Inc.)
- [Nordic Semiconductor Bluetooth Numbers Database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — confirms FEAF = Nest Labs Inc
- [Google Nest Thermostat technical specs](https://support.google.com/googlenest/answer/9230098) — confirms BLE 5.0 support
- openweave-core `src/ble/WeaveBleServiceData.h`: https://github.com/openweave/openweave-core/blob/master/src/ble/WeaveBleServiceData.h
- openweave-core `GenericConfigurationManagerImpl.ipp` (`_GetBLEDeviceIdentificationInfo`): https://github.com/openweave/openweave-core/blob/master/src/adaptations/device-layer/include/Weave/DeviceLayer/internal/GenericConfigurationManagerImpl.ipp
- openweave-core `WeaveVendorIdentifiers.hpp`: https://github.com/openweave/openweave-core/blob/master/src/lib/core/WeaveVendorIdentifiers.hpp
- openweave-core `NestProductIdentifiers.hpp`: https://github.com/openweave/openweave-core/blob/master/src/lib/profiles/vendor/nestlabs/device-description/NestProductIdentifiers.hpp
- openweave-core pairing codes: https://github.com/openweave/openweave-core/blob/master/src/lib/support/pairing-code/PairingCodeUtils.h and https://github.com/openweave/openweave-core/blob/master/src/lib/support/verhoeff/Verhoeff32.cpp
- openweave-core default BLE name: https://github.com/openweave/openweave-core/blob/master/src/adaptations/device-layer/include/Weave/DeviceLayer/WeaveDeviceConfig.h
- Google Help, "How to tell which Nest Protect you have": https://support.google.com/googlenest/answer/9232605
- Nest open source, nest-learning-thermostat u-boot `diamond3`: https://nest-open-source.googlesource.com/nest-learning-thermostat/5.1.9/u-boot/+/7d16fe590021414c36e66679c3ad4d10fd605056/bin/diamond3
- Bluetooth SIG assigned numbers (0xFEAF = Nest Labs Inc.): https://www.bluetooth.com/specifications/assigned-numbers/
