# iNode Energy Meter — Power Monitoring

## Overview

iNode Energy Meter is a BLE device that clamps onto the pulse LED of an electricity meter and counts pulses to calculate energy consumption. Broadcasts cumulative energy and average power passively.

## Identification

- **Manufacturer data pattern:** Fourth byte = `0x82`
- **Device type prefixes:** `0x90 0x82`, `0x92 0x82`, `0x94 0x82`, `0x96 0x82`
- **Note:** No registered company ID — identification is by the `0x82` magic byte at offset 3

## Advertisement Format

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Device type | Upper nibble: `0x90`=standard, `0x92`=with light sensor, `0x94`=dual tariff, `0x96`=3-phase |
| 1 | 1 | Flags | Bitfield: measurement mode, units |
| 2 | 1 | Reserved | `0x00` |
| 3 | 1 | Identifier | `0x82` (iNode magic byte) |
| 4-7 | 4 | Total pulses | uint32 LE — cumulative pulse count since reset |
| 8-9 | 2 | Average power | uint16 LE — instantaneous power in watts |
| 10-11 | 2 | Battery voltage | uint16 LE — millivolts |
| 12 | 1 | Battery percent | uint8 — 0-100% |

## Energy Calculation

Energy in kWh requires knowing the meter's pulse rate (configured per installation):

```python
# Common pulse rates: 1000 imp/kWh, 2000 imp/kWh
pulses_per_kwh = 1000  # from meter specification
energy_kwh = total_pulses / pulses_per_kwh
```

## ParseResult Fields

- `total_pulses` (int): Cumulative pulse count
- `average_power` (int): Current power consumption in watts
- `battery_voltage` (int): Battery voltage in millivolts
- `battery_percent` (int): Battery level percentage
- `device_type` (str): "standard", "light_sensor", "dual_tariff", "three_phase"

## Notes

- The pulse count is cumulative and survives power cycles
- Average power is calculated by the device from pulse intervals
- Device type byte determines which features are available

## References

- http://support.inode.pl/docs/iNode%20Energy%20Meter%20-%20instruction%20manual.pdf
- https://github.com/1technophile/OpenMQTTGateway/pull/755
