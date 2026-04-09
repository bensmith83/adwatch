# FIXD OBD-II Scanner BLE Protocol

## Overview
FIXD is a consumer Bluetooth OBD-II diagnostic dongle that plugs into a
vehicle's on-board diagnostics port. It reads check engine light codes,
diagnostic trouble codes (DTCs), and vehicle health data, relaying them
to the FIXD phone app over BLE.

## Manufacturer
**FIXD Automotive** — Atlanta, GA. Consumer automotive diagnostics company.

## BLE Advertisement Structure

### Local Name
Always advertises as `FIXD` (exact match, no suffix or variant).

### Service UUIDs
| UUID | Description |
|------|-------------|
| `FFF0` | Vendor-specific OBD data service |

### Notes
- `FFF0` is a generic vendor-assigned 16-bit UUID used by many BLE devices,
  so matching requires the local name "FIXD" for disambiguation
- BLE 4.0+ peripheral mode
- Pairs with FIXD app for reading DTCs and vehicle health

## Identification
- **Primary**: Local name exactly `FIXD`
- **Secondary**: Service UUID `FFF0` (confirms OBD service)
- **Device class**: `automotive`

## Protocol Details
- GATT service under FFF0 with read/write/notify characteristics for
  OBD-II PID requests and responses
- Supports standard OBD-II PIDs (vehicle speed, RPM, coolant temp, etc.)
- Check engine light codes decoded by the phone app, not the dongle
- Always on while vehicle ignition is active; may continue advertising
  briefly after ignition off

## References
- FIXD app: fixdapp.com
- OBD-II PID standard: SAE J1979
