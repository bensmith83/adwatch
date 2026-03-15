# Amphiro/Oras Hydractiva — Smart Shower Head

## Overview

Amphiro digital shower heads (also sold as Oras Hydractiva Digital and Hansa) broadcast real-time water usage data during shower sessions via BLE. They measure water volume, temperature, duration, and energy consumption without requiring batteries (powered by a micro-turbine in the water flow).

## Identification

- **Service UUID:** `7f402200-504f-4c41-5261-6d706869726f` (128-bit, contains "Amphiro" in ASCII)
- **Also uses:** `0x180A` (Device Information Service)

## Advertisement Format

Custom service data on the 128-bit UUID:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0-3 | 4 | Session ID | uint32 LE — shower session counter |
| 4-5 | 2 | Water volume | uint16 LE / 10 = liters |
| 6-7 | 2 | Water temperature | uint16 LE / 10 = degrees C |
| 8-9 | 2 | Shower duration | uint16 LE = seconds |
| 10-11 | 2 | Energy | uint16 LE = Wh (energy to heat the water) |

## ParseResult Fields

- `session_id` (int): Shower session number
- `water_volume` (float): Total water used (liters)
- `water_temperature` (float): Average water temperature (C)
- `duration` (int): Shower duration in seconds
- `energy` (int): Energy consumed heating water (Wh)

## Notes

- Data is only broadcast during active shower sessions
- Device is self-powered — no battery to monitor
- 128-bit UUID matching requires full UUID comparison, not short UUID

## References

- https://github.com/chkuendig/hass-amphiro-ble
- https://gitlab.com/baze/amphiro_oras_bluetooth_shower_hub/-/tree/main/Protocol_description
