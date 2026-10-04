# EcoFlow (Portable Power Stations)

## Overview

EcoFlow Delta, River, and PowerStream devices broadcast BLE advertisements for device discovery and pairing. Advertisements contain device identification (serial number, product type) but rich telemetry (battery level, power data) requires an authenticated connection.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xB5B5` | Custom/unregistered, used across all EcoFlow BLE devices |
| Company ID | `0xA4A8` | Custom/unregistered; second ID the EcoFlow app scan-filters on |
| ~~Company ID~~ | ~~`0x0BA9`~~ | **Not EcoFlow.** The app also scan-filters on `0x0BA9`, but the Bluetooth SIG Assigned Numbers registry assigns it to Allterco Robotics (Shelly); all corpus `0x0BA9` frames are Shelly BLU. Handled by `shelly_blu`, not `ecoflow`. |
| Local name | `EF-*` (often absent) | Prefix `EF-` followed by serial number chars — not reliably advertised; see Corpus Notes |

### Manufacturer Data Layout

| Offset | Size | Field | Encoding | Notes |
|--------|------|-------|----------|-------|
| 0 | 1 | Protocol version | uint8 | |
| 1-16 | 16 | Serial number | ASCII | e.g. `R331xxxxxxxxxxxx` |
| 17 | 1 | Status | bits 0-6 = state of charge %, bit 7 = **dormancy** (`active` = not dormant) | see note below |
| 18 | 1 | Product type / OTA | bits 7-6 upgrade status, bits 5-0 config | |
| 19 | 1 | Charge / sleep | bit 2 = charging; `(x & 3) == 1` = sleeping | |
| 20 | 1 | Config / pairing state (V1 families) | uint8 | |
| 21 | 1 | Reserved | — | |
| 22 | 1 | Capability flags | bitfield (see below) | |

If manufacturer data < 20 bytes, defaults: status=0, product_type=0.

**Byte 17, bit 7 (corrected 2026-09-30).** This doc previously called bit 7
an "active flag". The plugin's layout — verified against the decompiled
`com.ecoflow` app (apk-ble-hunting `ecoflow_passive.md`, report offset M+21)
— reads bits 0-6 as state-of-charge % and bit 7 as a *dormancy* flag. The
corpus agrees: in all 47 `0xB5B5` frames bit 7 is clear while bits 0-6 carry
plausible SoC values (0-100, e.g. `0x43` = 67 %, `0x64` = 100 %), which only
makes sense if bit 7 = dormant and the unit is awake. So `dormant = bit7`,
`active = not dormant`. (The u0/p0 families reuse the byte as
`deviceAddFlag` bit 7 + `deviceAddStateCode` bits 0-6.)

### Capability Flags (byte 22)

| Bits | Mask | Field |
|------|------|-------|
| 0 | `0x01` | Encrypted communication |
| 1 | `0x02` | Supports verification |
| 2 | `0x04` | Verified/paired |
| 3-5 | `0x38` >> 3 | Encryption type (0–7) |
| 6 | `0x40` | Supports 5GHz WiFi |

### Serial Number Prefixes → Device Model

| Prefix | Device |
|--------|--------|
| `R331`/`R335` | DELTA 2 |
| `R351`/`R354` | DELTA 2 Max |
| `P231` | DELTA 3 |
| `D3N1` | DELTA 3 Classic |
| `DCA`/`DCF`/`DCK` | DELTA Pro |
| `MR51` | DELTA Pro 3 |
| `Y711` | DELTA Pro Ultra |
| `R601`/`R603` | RIVER 2 |
| `R611`/`R613` | RIVER 2 Max |
| `R631`/`R634` | RIVER 3 Plus |
| `HW51` | PowerStream |
| `HD31` | Smart Home Panel 2 |
| `DB` | DELTA mini |

(Many more prefixes exist — see ha-ef-ble source for full mapping.)

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device present | company_id match | EcoFlow device nearby |
| Serial number | bytes 1–16 | ASCII, identifies specific unit |
| Device model | serial prefix | Map prefix → product name |
| State of charge | byte 17, bits 0-6 | Percent (0-100) |
| Dormant / active | byte 17, bit 7 | bit set = dormant; `active` = not dormant |
| Charging / sleeping | byte 19 | bit 2 charging; low 2 bits == 1 sleeping |
| Encryption status | byte 22 | Whether BLE comms are encrypted |

### What We Cannot Parse from Advertisements

- Charge/discharge power (watts)
- AC/DC/USB port states
- Temperature
- Solar input

All telemetry requires authenticated GATT connection with ECDH key exchange + AES-CBC encryption.

## Corpus Notes (2026-07-17 sweep)

Findings from real telemetry — a small sample, so field observations rather
than spec:

- **Identification is no longer name-gated.** The parser previously required
  the local name to start with `"EF-"`. In the corpus most units don't
  reliably advertise that name at all: 7 of 8 sampled records had no local
  name, and the one that did carried a bare serial-like `"R33-3221"` with no
  `"EF-"` prefix. The parser now identifies EcoFlow units by company ID
  `0xB5B5` **plus a decodable ASCII serial in the payload** — no local name
  required. The `EF-*` prefix, when present, is still a corroborating signal
  but is no longer a precondition.

### Open questions (for a future pass)

1. **Undocumented byte at offset 23.** The byte table above documents offsets
   0–22. Real captures carry a byte at offset 23 that isn't in the table; its
   meaning is unknown. Needs more samples before assigning it.
2. **Long-variant advertisement (~42 bytes).** One record ran ~42 bytes
   rather than the documented ~21–23. After the documented fields it appends
   what looks like a *second* vendor sub-record, opening with a repeated-byte
   marker `c5 c5`. Uninterpreted — only one sample seen so far, so we're not
   decoding it yet.

## References

- **Bluetooth SIG Assigned Numbers** (company identifiers): https://bitbucket.org/bluetooth-SIG/public/src/main/assigned_numbers/company_identifiers/company_identifiers.yaml — `0x0BA9` = Allterco Robotics ltd (Shelly)
- **Decompiled app**: apk-ble-hunting `reports/ecoflow_passive.md` (Stage 4b; `EFSmartDeviceCenterManager.java:105-107` scan filters, `el/i.java` status-byte decode)
- **RE repo**: https://github.com/rabits/ef-ble-reverse
- **HA integration**: https://github.com/rabits/ha-ef-ble
- **Delta 2 RE**: https://github.com/nielsole/ecoflow-bt-reverse-engineering
