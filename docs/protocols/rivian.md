# Rivian Vehicle BLE Protocol

## Overview

Rivian electric vehicles (R1T, R1S, R2, R3) and their associated phone key feature broadcast BLE advertisements. Two modes observed: phone key pairing mode and vehicle broadcast mode.

## Identifiers

- **Company ID:** `0x0941` (likely Rivian Automotive — recently assigned, not in older BT SIG databases)
- **Local names:** `Rivian Phone Key`, `RIVN`
- **Custom UUIDs:**
  - `3DB57984-B50C-509B-BCE5-153071780C83` — Phone Key mode
  - `6F65732A-5F72-6976-3031-7446B3C9CBC9` — Vehicle mode (note: `6F65732A5F72697630317446` decodes to ASCII `oes*_riv01tF` — partial "Rivian" string)
- **Device class:** `vehicle`, `vehicle_key`

## Advertisement Formats

### Phone Key Mode

```
Local name: "Rivian Phone Key"
Company ID: 0x0941
Manufacturer data: 41090101061a0363 (8 bytes)
Service UUID: 3DB57984-B50C-509B-BCE5-153071780C83

Breakdown:
  4109    company ID (LE)
  01      version/type (phone key)
  01      status
  06      flags
  1a      unknown
  03      unknown
  63      unknown
```

### Vehicle Mode

```
Local name: "RIVN"
Company ID: 0x0941
Manufacturer data: 4109170900 (5 bytes)
Service UUID: 6F65732A-5F72-6976-3031-7446B3C9CBC9

Breakdown:
  4109    company ID (LE)
  17      type (vehicle broadcast?)
  09      unknown
  00      unknown
```

### Passive Mode (name only)

```
Local name: "Rivian Phone Key"
No manufacturer data
No service UUIDs
```

## Parsing Strategy

1. Match on company_id `0x0941` OR local_name pattern `^Rivian|^RIVN`
2. Determine mode:
   - If manufacturer data byte 2 = `0x01` → phone key
   - If manufacturer data byte 2 = `0x17` → vehicle
   - If name only → passive phone key
3. Extract what fields are available
4. Report device type, mode, presence

## Device Classification

| Pattern | Device Class | Type |
|---------|-------------|------|
| `Rivian Phone Key` | vehicle_key | Phone acting as car key |
| `RIVN` | vehicle | Vehicle broadcasting |

## Known Limitations

- Proprietary Rivian protocol — no official documentation
- Manufacturer data fields beyond company ID are speculative
- Vehicle authentication data is encrypted
- Limited samples (3 ads)

## References

- Rivian uses BLE for phone-as-key feature (digital key)
- Company ID `0x0941` not in older Bluetooth SIG databases — recently assigned
- Similar to Tesla BLE key protocol concept
