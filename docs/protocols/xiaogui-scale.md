# Xiaogui Scale — Baby/Body Scale

## Overview

White-label smart scales sold under various brands (Xiaogui, TZC4, and many unbranded). Unlike Xiaomi Mi Scale which uses standard BLE Weight Scale service data, Xiaogui scales use manufacturer-specific data with a different byte layout.

## Identification

- **Manufacturer data:** Xiaogui-specific prefix bytes (brand identifier in first bytes)
- **Local name:** May contain model-specific patterns

## Advertisement Format

Manufacturer-specific data (`0xFF` AD type):

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Control flags | Bitfield: bit 0 = stabilized, bit 4 = unit (0=kg, 1=lbs), bit 5 = impedance present |
| 1-2 | 2 | Impedance | uint16 LE — ohms (body composition models only, if flags bit 5 set) |
| 3-4 | 2 | Weight | uint16 LE / 10 = kg (or / 10 = lbs depending on unit flag) |
| 5+ | var | Padding/timestamp | Variable — may contain timestamp or zeros |

### Control Flags

| Bit | Meaning |
|-----|---------|
| 0 | Measurement stabilized (weight locked) |
| 1 | Weight removed from scale |
| 4 | Unit: 0 = kg, 1 = lbs |
| 5 | Impedance data present |

## ParseResult Fields

- `weight` (float): Weight in kg or lbs (depending on unit)
- `unit` (str): "kg" or "lbs"
- `stabilized` (bool): Whether measurement is stable/locked
- `impedance` (int): Body impedance in ohms (body composition models, None otherwise)
- `weight_removed` (bool): Whether weight was just removed

## Notes

- Very similar concept to Xiaomi Mi Scale but different byte layout
- Impedance is only present on body composition models
- Weight updates broadcast in real-time during measurement, with `stabilized` flag indicating final reading

## References

- https://github.com/custom-components/ble_monitor/discussions/560
