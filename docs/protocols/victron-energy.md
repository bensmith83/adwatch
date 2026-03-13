# Victron Energy (Instant Readout)

## Overview

Victron Energy makes solar charge controllers, battery monitors, inverters, and other power electronics popular in off-grid/RV/marine setups. Devices broadcast real-time energy data via BLE using an encrypted "Instant Readout" protocol. The unencrypted header contains device identification; decrypted payloads contain voltage, current, power, state of charge, etc.

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

## References

- [victron-ble](https://github.com/keshavdv/victron-ble) — Python parser (primary reference)
- [esphome-victron_ble](https://github.com/Fabian-Schmidt/esphome-victron_ble) — ESPHome component
- [Victron Community — BLE Protocol](https://community.victronenergy.com/questions/187303/victron-bluetooth-advertising-protocol.html)
