# Mopeka Pro Check — BLE Tank Level Sensor

## Overview

Mopeka Pro Check sensors use ultrasonic time-of-flight measurement to determine propane/LPG tank fill levels. Popular in RV, off-grid, and BBQ setups. Also sold as Lippert/LCI tank sensors.

## Identification

- **Local name:** Starts with `M` followed by hex characters (e.g., `M1234ABCD`)
- **Manufacturer data:** Mopeka-specific prefix bytes in advertisement

## Advertisement Format

Manufacturer-specific data (variable length):

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Hardware ID | uint8 — sensor hardware revision |
| 1 | 1 | Sensor type | uint8 — `0x03`=Pro Check, `0x05`=Pro Plus, `0x08`=Pro Plus Gen2 |
| 2 | 1 | Battery | uint8 — raw value, voltage = `(value / 32.0) * 2.0 + 1.5` V |
| 3 | 1 | Temperature | uint8 — offset encoding: `value - 40` = degrees C |
| 4-5 | 2 | Raw level | uint16 LE — ultrasonic time-of-flight in microseconds |
| 6 | 1 | Quality | bits 7-6: `0x03`=HIGH, `0x02`=MEDIUM, `0x01`=LOW, `0x00`=NO_READING |
| 7 | 1 | Flags | bit 0: sync button pressed, bit 1: has accelerometer |
| 8-9 | 2 | Accel X | int16 LE (optional, if flags bit 1 set) |
| 10-11 | 2 | Accel Y | int16 LE (optional) |

## Level Calculation

The raw ultrasonic value must be converted to a fill percentage:

```
speed_of_sound = 1450  # m/s in propane
distance_mm = (raw_level * speed_of_sound) / 2000
fill_percent = (distance_mm / configured_tank_height_mm) * 100
```

Standard tank heights:
- 20 lb (typical BBQ): ~254 mm
- 30 lb: ~381 mm
- 40 lb: ~508 mm
- 100 lb: ~762 mm

## ParseResult Fields

- `tank_level_raw` (int): Raw ultrasonic time-of-flight (microseconds)
- `temperature` (float): Sensor temperature (C)
- `battery_voltage` (float): Battery voltage (V)
- `reading_quality` (str): "high", "medium", "low", "no_reading"
- `sync_pressed` (bool): Sync button state
- `sensor_type` (str): "pro_check", "pro_plus", "pro_plus_gen2"

## References

- https://github.com/spbrogan/mopeka_pro_check
- https://esphome.io/components/sensor/mopeka_pro_check/
