# Midea Smart Appliance BLE Protocol

## Overview

GD Midea Air-Conditioning Equipment Co., Ltd. is a major Chinese manufacturer of HVAC, air conditioners, dehumidifiers, washers, and other smart appliances (also marketed under Comfee, Inventor EVO, Toshiba HA, and others). Many of their newer Wi-Fi-enabled appliances ship with a BLE chip used for the initial network onboarding flow ("EasyAir" / "Midea Air" app pairing). While in this onboarding state — and intermittently afterward — the appliance broadcasts a BLE advertisement containing its serial number.

The local name `net` is the give-away: the appliance is announcing that it is in network-setup mode.

## Identifiers

- **Company ID:** `0x06A8` (GD Midea Air-Conditioning Equipment Co., Ltd.)
- **Local name:** `net` (often the only device name advertised during pairing mode)
- **Device class:** `appliance`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x06A8` (`a8 06` LE) | Always Midea |
| Local name | `net` | Setup-mode marker |
| Service UUID | none observed | Pure manufacturer-data beacon |
| Service Data | none observed | — |

### Manufacturer Data Layout

Two frame variants observed in the wild:

#### Variant A — Short frame (17 bytes)

```
a8 06 01 30 30 30 30 30 51 31 35 41 43 31 38 42 36
└─CID─┘ │  └────────── ASCII serial (14 bytes) ──┘
        └─ Frame type (0x01 = serial-only)
```

#### Variant B — Long frame (28 bytes)

```
a8 06 01 30 30 30 30 30 51 31 35 41 43 31 38 42 36 01 41 1c 32 b7 18 a5 74 b8 54 00
└─CID─┘ │  └────────── ASCII serial (14 bytes) ──┘ │  └────── BD addr (6 bytes) ──┘ └── pad/status ──┘
        └─ Frame type (0x01)                       └─ Sub-marker (0x01 = MAC follows)
```

| Offset | Length | Description |
|--------|--------|-------------|
| 0-1 | 2 | Company ID `0x06A8` (LE) |
| 2 | 1 | Frame type — `0x01` observed |
| 3-16 | 14 | ASCII serial number (e.g. `"00000Q15AC18B6"`) |
| 17 | 1 | Sub-frame marker (long frame only) |
| 18-23 | 6 | Bluetooth device address (long frame only) |
| 24-27 | 4 | Status / pad bytes (long frame only) |

### Serial Number Format

The 14-byte ASCII string follows Midea's SN convention:

- **Bytes 0-4:** Padding zeros (`"00000"`) — used by Midea cloud to detect Wi-Fi vs cellular onboarding
- **Byte 5:** Device family code — `Q` (portable AC), `M` (mini-split), etc.
- **Bytes 6-13:** 8-character device unique ID (hex-like), typically a truncated Wi-Fi MAC suffix plus batch code

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Manufacturer | company_id | Always GD Midea |
| Setup mode | local_name `"net"` | Appliance is in network-pairing mode |
| Serial number | manufacturer_data[3:17] | ASCII, 14 bytes |
| Family code | serial_number[5] | `Q`, `M`, etc. |
| BD address | manufacturer_data[18:24] | Long-frame only |

### What We Cannot Parse (requires GATT connection / cloud)

- Power state, set-point, mode, fan speed
- Real product model
- Firmware version
- Wi-Fi credentials negotiation (this happens after BLE-GATT handshake)

## Sample Advertisements

```
Variant A (short):
  Company ID:        0x06A8 (Midea)
  Local name:        net
  Manufacturer data: a806013030303030513135414331384236
  Serial number:     00000Q15AC18B6
  Sightings:         2

Variant B (long):
  Company ID:        0x06A8 (Midea)
  Local name:        net
  Manufacturer data: a80601303030303051313541433138423601411c32b718a574b85400
  Serial number:     00000Q15AC18B6
  Embedded BD addr:  41:1c:32:b7:18:a5
  Sightings:         8
```

## Identity Hashing

```
identifier = SHA256("midea_appliance:{serial_number}")[:16]
```

The serial number is more stable than the BLE MAC (which can be a randomized resolvable private address during onboarding).

## Detection Significance

- Indicates a Midea-built smart appliance is currently in network-pairing mode
- Common products: Midea/Comfee portable ACs, mini-splits, dehumidifiers, washers, microwaves
- Setup mode usually lasts a few minutes after factory reset or after pressing the dedicated pairing button — persistent presence implies the user is having trouble onboarding
- After successful onboarding, the BLE radio typically sleeps and the appliance falls back to Wi-Fi

## Parsing Strategy

1. Match on `company_id == 0x06A8` OR `local_name == "net"` AND `company_id == 0x06A8`
2. Validate `manufacturer_payload[0] == 0x01` (frame type)
3. Extract 14-byte ASCII serial from `manufacturer_payload[1:15]`
4. If `len(manufacturer_payload) >= 22` and `manufacturer_payload[15] == 0x01`, extract BD address from bytes 16-21
5. Return device class `appliance`

## References

- Bluetooth SIG Company ID: `0x06A8` = GD Midea Air-Conditioning Equipment Co., Ltd.
- [midea-beautiful-air](https://github.com/nbogojevic/midea-beautiful-air) — Python reverse-engineered Midea LAN protocol
- [midea_ac_lan](https://github.com/georgezhao2010/midea_ac_lan) — Home Assistant Midea integration
- Midea EasyAir / Midea Air Mobile App onboarding flow
