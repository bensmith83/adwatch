# HLI Solutions / GE Current Lighting (NX Lighting Controls)

## Overview

HLI Solutions Inc. (formerly GE Current, a Daintree company; now under Hubbell Lighting) manufactures commercial smart building lighting controls and occupancy sensors. Their NX Lighting Controls platform uses BLE advertisements to broadcast sensor presence and room/zone information for building management systems.

These sensors are typically found in commercial offices, conference rooms, and open-plan workspaces. The BLE advertisements include the sensor's assigned room/zone name (e.g., "235 Open Office").

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x06DF` (1759) | HLI Solutions Inc. (little-endian bytes: `df 06`) |
| Local Name | Room/zone name | e.g., "235 Open Office" — may not be present in every ad |

### Manufacturer Data Layout

Total payload: 17 bytes (2-byte company ID + 15 bytes data)

```
Offset  Bytes  Field              Example       Notes
------  -----  -----------------  ------------  ---------------------------
0-1     2      Company ID (LE)    df 06         0x06DF = HLI Solutions
2       1      Protocol version?  00            Constant across samples
3       1      Device type?       7e            Constant across samples (0x7E = 126)
4-7     4      Unknown header     00 00 00 01   Possibly firmware/config version
8       1      Unknown            01            Constant
9-10    2      Channel/config?    fe ff         Constant across samples
11      1      Unknown            7f            Constant
12      1      Unknown            00            Constant
13      1      Zone/sensor ID     29/33/20      Varies per device — possibly zone ID
14-16   3      Unknown trailer    01 05 92      Constant across samples
```

### Observed Payloads

| Manufacturer Data (hex)                    | Local Name        | Notes |
|--------------------------------------------|-------------------|-------|
| `df06007e0000000101feff7f0029010592`        | 235 Open Office   | Zone ID 0x29 (41) |
| `df06007e0000000101feff7f0029010592`        | (none)            | Same device, name not in every ad |
| `df06007e0000000101feff7f0033010592`        | (none)            | Zone ID 0x33 (51) |
| `df06007e0000000101feff7f0020010592`        | (none)            | Zone ID 0x20 (32) |

### Key Observations

- Byte 13 is the only field that varies between different sensors — likely a zone or sensor ID
- The local name contains human-readable room/zone names assigned during commissioning
- Not every advertisement includes the local name (BLE scan response vs advertisement)
- All observed sensors share identical bytes except byte 13, suggesting a single installation/network
- RSSI range -89 to -97 indicates typical commercial building distances

## What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Sensor presence | Company ID match | HLI/GE Current sensor nearby |
| Room/zone name | Local name | When present in scan response |
| Zone ID | Byte 13 of mfr data | Numeric zone identifier |
| Device type | Byte 3 of mfr data | 0x7E observed; may vary by sensor model |

## What We Cannot Parse

- Occupancy state (likely requires GATT connection)
- Light level readings
- Sensor battery status
- Network/group membership details

## Detection Significance

- Indicates a commercial building with smart lighting controls
- Room names reveal building layout and space usage
- Multiple zone IDs suggest multi-zone lighting installation
- Useful for mapping commercial BLE environments

## References

- **Bluetooth SIG Company ID**: 0x06DF — HLI Solutions Inc.
- **Product Line**: Current Lighting NX Controls — https://www.currentlighting.com/controls/sensors
- **Formerly**: GE Current, a Daintree company (acquired by Hubbell/HLI ~2022)
