# Victron Energy (Instant Readout + Vendor Beacon)

## Overview

Victron Energy makes solar charge controllers, battery monitors, inverters, and other power electronics popular in off-grid/RV/marine setups. We see **two distinct BLE streams** from Victron hardware, handled by the same parser but emitting different `beaconType` values so downstream consumers can tell them apart:

| Stream | CID | Spec | What it carries |
|--------|-----|------|-----------------|
| **Instant Readout** | `0x02E1` (SIG-registered) | Victron "Extra Manufacturer Data 2022-12-14" PDF | Encrypted live telemetry (voltage / current / power / SoC) |
| **Vendor Beacon** | `0x4556` (NOT SIG-registered — "VE" ASCII magic) | No public spec | Identification-only — friendly-name label |

The Instant Readout stream is what most existing community tooling targets; the Vendor Beacon is a separate stream that some Victron WiFi-equipped devices emit alongside (or instead of) Instant Readout. The CID `0x4556` is **not** allocated by the Bluetooth SIG — Victron is stuffing ASCII "VE" into the company-ID slot non-conformantly.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x02E1` | Victron Energy B.V. |
| Prefix byte | `0x10` | First byte of manufacturer data = Instant Readout format |
| Service UUID | None | Uses manufacturer data only |
| Local name | Not used | — |

### Manufacturer Data Layout

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | Prefix | 1 byte | Must be `0x10` | — |
| 1 | Reserved | 1 byte | — | — |
| 2-3 | Model ID | uint16 LE | Maps to 600+ product names | — |
| 4 | Record Type | uint8 | Device class (see below) | — |
| 5-6 | IV / Data Counter | uint16 LE | AES-CTR nonce, increments per reading | — |
| 7 | Key Byte 0 | uint8 | First byte of AES key (for validation) | — |
| 8+ | Encrypted Payload | up to 16 bytes | AES-128-CTR encrypted sensor data | — |

### Record Types (Device Classes)

| Byte | Device Type |
|------|-------------|
| `0x01` | Solar Charger |
| `0x02` | Battery Monitor (SmartShunt) |
| `0x03` | Inverter |
| `0x04` | DC-DC Converter |
| `0x05` | Smart Lithium |
| `0x08` | AC Charger |
| `0x09` | Smart Battery Protect |
| `0x0A` | Lynx Smart BMS |
| `0x0B` | Multi RS |
| `0x0C` | VE.Bus |
| `0x0D` | DC Energy Meter |
| `0x0F` | Orion XS |

Special model IDs: `0xA3A4` and `0xA3A5` are Battery Sense (uses Battery Monitor parser).

### Encryption

- **Algorithm:** AES-128-CTR
- **Key:** 16-byte per-device key from VictronConnect app (Product Info > Instant Readout Details)
- **Nonce:** 16-byte array, bytes [0:2] = the IV from header, rest zeros
- **Validation:** `encrypted_data[0]` must equal `key[0]`, then discard that byte before decrypting
- **Padding:** PKCS7 to 16-byte boundary before decryption

```python
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Util.Padding import pad

key = bytes.fromhex(advertisement_key_hex)
# Validate: encrypted_data[0] == key[0]
ctr = Counter.new(128, initial_value=iv_uint16, little_endian=True)
cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
decrypted = cipher.decrypt(pad(encrypted_data[1:], 16))
```

### Decrypted Payload: Solar Charger (0x01) — 89 bits, LSB-first

| Field | Bits | Type | Scale | Null |
|-------|------|------|-------|------|
| Charge State | 8 | unsigned | OperationMode enum | 0xFF |
| Charger Error | 8 | unsigned | ChargerError enum | 0xFF |
| Battery Voltage | 16 | signed | ×0.01 V | 0x7FFF |
| Battery Current | 16 | signed | ×0.1 A | 0x7FFF |
| Yield Today | 16 | unsigned | ×10 Wh | 0xFFFF |
| PV Power | 16 | unsigned | 1 W | 0xFFFF |
| External Load | 9 | unsigned | ×0.1 A | 0x1FF |

### Decrypted Payload: Battery Monitor (0x02) — 102 bits

| Field | Bits | Type | Scale | Null |
|-------|------|------|-------|------|
| Remaining Mins | 16 | unsigned | 1 min | 0xFFFF |
| Voltage | 16 | signed | ×10 mV | 0x7FFF |
| Alarm Reason | 16 | unsigned | flags | — |
| Aux Value | 16 | unsigned | mV or Kelvin | — |
| Aux Mode | 2 | unsigned | 0=starter V, 1=midpoint, 2=temp, 3=disabled | — |
| Current | 22 | signed | 1 mA | — |
| Consumed Ah | 20 | unsigned | ×0.1 Ah | — |
| State of Charge | 10 | unsigned | ×0.1% | — |

### Decrypted Payload: Inverter (0x03) — 82 bits

| Field | Bits | Type | Scale | Null |
|-------|------|------|-------|------|
| Device State | 8 | unsigned | OperationMode enum | 0xFF |
| Alarm Reason | 16 | unsigned | flags | — |
| Battery Voltage | 16 | signed | ×0.01 V | 0x7FFF |
| AC Apparent Power | 16 | unsigned | 1 VA | 0xFFFF |
| AC Voltage | 15 | unsigned | ×0.01 V | 0x7FFF |
| AC Current | 11 | unsigned | ×0.1 A | 0x7FF |

### Key Enums

**OperationMode:** OFF(0), LOW_POWER(1), FAULT(2), BULK(3), ABSORPTION(4), FLOAT(5), STORAGE(6), EQUALIZE_MANUAL(7), INVERTING(9), POWER_SUPPLY(11), STARTING_UP(245), REPEATED_ABSORPTION(246), RECONDITION(247), BATTERY_SAFE(248), ACTIVE(249), EXTERNAL_CONTROL(252), NOT_AVAILABLE(255)

### What We Can Parse from Advertisements

**Without encryption key (always):**

| Field | Source | Notes |
|-------|--------|-------|
| Model name | mfr_data[2:4] | 600+ known product IDs |
| Device class | mfr_data[4] | Solar/battery/inverter/etc. |
| Data freshness | mfr_data[5:7] | Counter increments per new reading |
| Key validation | mfr_data[7] | Can verify if user's key is correct |

**With encryption key (optional user config):**

| Field | Source | Notes |
|-------|--------|-------|
| Battery voltage/current | Decrypted payload | Per device class |
| Solar yield/power | Decrypted payload | Solar charger only |
| State of charge | Decrypted payload | Battery monitor only |
| AC power/voltage | Decrypted payload | Inverter only |
| Device state | Decrypted payload | Charge state, alarms |

## Identity Hashing

```
identifier = SHA256("{mac}:{model_id}")[:16]
```

## Detection Significance

- Extremely popular in off-grid, RV, marine, and solar communities
- Broadcasts continuously (~1 second intervals)
- Device identification alone is valuable (model + class)
- Full sensor data available with per-device AES key
- 14 device classes covering solar, battery, inverter, DC-DC, BMS, etc.

## Vendor Beacon Stream (CID `0x4556`, "VE" ASCII magic)

A second BLE stream that some Victron devices emit — particularly the WiFi-equipped variants (Smart Battery Sense w/ Wi-Fi, Smart MPPT, EV Charging Station NS, etc.). Identification-only; no telemetry.

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x4556` (LE-read of bytes `56 45` = ASCII "VE") | NOT SIG-assigned — Victron stuffs ASCII into the CID slot non-conformantly |
| Magic header (full 4 bytes) | `56 45 52 15` | Required exactly to avoid false positives from any other firmware emitting `56 45` |
| Local name pattern | `<label>.A<2hex>.WIFI` (e.g. `Smart.A7.WIFI`, `Lola's E.A5.WIFI`) | Last 2 hex chars before `.WIFI` look like the low byte of the BLE MAC; the `.WIFI` suffix marks Wi-Fi-capable firmware variants |

### Wire Format

```
56 45 52 15 | <up to 16 ASCII bytes>
└────┬────┘ └─────────┬───────────┘
     │                └── user-set device label (truncated to 16 bytes,
     │                    NUL- or space-padded)
     └── 4-byte magic "VE" + 0x52 ("R") + 0x15
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0-1    | `56 45` | "VE" magic | ASCII bytes in the CID slot |
| 2      | `52` | "R" ASCII | Constant across captures — possibly marks "VER" (VE Record) |
| 3      | `15` | Unknown | Constant across captures — likely a frame-type / version byte; not enough samples to map values to product types |
| 4-19   | up to 16 bytes | ASCII label | Friendly device name set via VictronConnect; trailing space or NUL padding |

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | magic `56 45 52 15` | Victron Energy (vendor-beacon stream) |
| Label | mfg bytes 4..20 | Trimmed of trailing whitespace / NUL |

### What We Cannot Parse

- Specific product model — the `0x15` byte may encode this but is constant in our captures
- Live telemetry — this stream does not carry it; if the same device also emits the Instant Readout stream, that's where the data lives
- Whether `0x15` distinguishes product types (Smart MPPT vs Smart Battery Sense vs EV Charging Station NS, etc.) — needs more samples across known device types

### Identity Hashing

```
identifier = SHA256(mac_address)[:16]
```

The vendor-beacon stream carries no stable per-emitter id in the payload (the magic is fleet-constant, the label is user-set), so we fall back to the BLE MAC.

### Why "Vendor Beacon" Has No Published Spec

No published spec exists for the `0x4556` / `VE\x52\x15` stream. The major community Victron BLE projects (`keshavdv/victron-ble`, `Fabian-Schmidt/esphome-victron_ble`, Home Assistant's `victron_ble` integration) all gate strictly on CID `0x02E1` + leading byte `0x10`. The vendor-beacon stream is presumably internal to Victron's app or a Wi-Fi-bridge firmware variant; our decoding is empirical from captures.

If you want richer field decoding here, the next step is to capture more samples across known product types (Smart Battery Sense, SmartShunt, EV Charging Station NS, GlobalLink 520) and watch whether byte 3 (`0x15`) varies — that's the most likely product-type discriminator.

## References

- [victron-ble](https://github.com/keshavdv/victron-ble) — Python parser for Instant Readout (primary reference)
- [esphome-victron_ble](https://github.com/Fabian-Schmidt/esphome-victron_ble) — ESPHome component
- [Victron Community — BLE Protocol](https://community.victronenergy.com/questions/187303/victron-bluetooth-advertising-protocol.html)
- [Victron Extra Manufacturer Data PDF](https://communityarchive.victronenergy.com/storage/attachments/extra-manufacturer-data-2022-12-14.pdf) — Instant Readout spec
- [Nordic `bluetooth-numbers-database`](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — confirms Victron has only one SIG-registered CID (`0x02E1`), so `0x4556` is vendor-claimed not SIG-allocated
