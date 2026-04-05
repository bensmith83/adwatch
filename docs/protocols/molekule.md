# Molekule Air Purifier BLE Protocol

## Overview

Molekule makes PECO (Photo Electrochemical Oxidation) air purifiers. Their devices advertise via BLE using the assigned service UUID FE4F and a local name pattern `MOLEKULE_XXXX`. The manufacturer data contains an ASCII-encoded string with model and serial number information.

## Identifiers

- **Service UUID:** `FE4F` (16-bit, Bluetooth SIG assigned)
- **Local name pattern:** `MOLEKULE_XXXX` (suffix is a device identifier, e.g., `MOLEKULE_0868`)
- **Device class:** `air_purifier`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FE4F` (full: `0000fe4f-0000-1000-8000-00805f9b34fb`) | Bluetooth SIG assigned to Molekule |
| Local name | `MOLEKULE_XXXX` | XXXX = device identifier |

### Manufacturer Data Structure

The manufacturer data is an ASCII-encoded string containing model and serial information, followed by a trailing non-ASCII byte (possibly a checksum).

#### Example (22 bytes)

```
4d 48 31 4d 2d 53 48 41 31 39 30 34 31 35 2d 30
30 30 38 36 38 e4
```

Decoded ASCII (ignoring trailing byte): `MH1M-SHA190415-000868`

| Segment | Value | Description |
|---------|-------|-------------|
| Model | `MH1M` | Hardware model identifier |
| Build/batch | `SHA190415` | Possibly SHA-prefix + date code (2019-04-15) |
| Serial | `000868` | Unit serial number |
| Trailing byte | `0xE4` | Checksum or status byte |

The local name suffix (`0868`) corresponds to the last 4 digits of the serial number.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | service_uuid or local_name | Molekule air purifier nearby |
| Device ID | local_name suffix | Matches serial number tail |
| Serial info | manufacturer_data (ASCII) | Model-batch-serial string |

### What We Cannot Parse (requires GATT connection)

- Filter status / replacement date
- Air quality readings
- Fan speed
- Operating mode
- Wi-Fi configuration

## Identity Hashing

```
identifier = SHA256("molekule:{mac}")[:16]
```

## Detection Significance

- Indicates a Molekule air purifier in the area
- Always-on BLE advertisement when device is powered
- Common in homes and offices

## Parsing Strategy

1. Match on service UUID `FE4F` OR local_name matching `^MOLEKULE_`
2. Extract device ID from local_name suffix
3. If manufacturer data present, decode as ASCII to extract model/serial string
4. Return device class `air_purifier`

## References

- [Molekule](https://molekule.com/) — manufacturer website
- Bluetooth SIG 16-bit UUID assignment: FE4F = Molekule, Inc.
