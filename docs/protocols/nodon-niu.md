# NodOn NIU — Smart Button

## Overview

NodOn NIU is a BLE smart button that broadcasts button press events without requiring an active connection. Supports single, double, triple, quad, quintuple, and long press detection. CR2032 battery powered.

## Identification

- **Local name:** Contains "NIU" or NodOn prefix
- **Manufacturer data:** NodOn-specific prefix bytes

## Advertisement Format

Manufacturer-specific data:

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Button event | uint8 — press type enum |
| 1 | 1 | Color code | uint8 — physical button color |
| 2 | 1 | Battery | uint8 = % |

### Button Event Values

| Value | Event |
|-------|-------|
| `0x01` | Single press |
| `0x02` | Double press |
| `0x03` | Triple press |
| `0x04` | Quad press |
| `0x05` | Quintuple press |
| `0x09` | Long press |
| `0x0A` | Release (after long press) |

### Color Codes

| Value | Color |
|-------|-------|
| `0x01` | White |
| `0x02` | Blue |
| `0x03` | Green |
| `0x04` | Red |
| `0x05` | Black |

## ParseResult Fields

- `button_event` (str): "single", "double", "triple", "quad", "quintuple", "long_press", "release"
- `button_color` (str): Physical button color name
- `battery` (int): Battery percentage

## References

- https://decoder.theengs.io/devices/NODONNIU.html
- https://github.com/NodonLab/NIU-SDK
