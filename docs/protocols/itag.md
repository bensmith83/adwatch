# iTAG (BLE Anti-Loss Tracker)

## Overview

iTAG is an extremely common, cheap (~$2) BLE anti-loss keyfinder/tracker. Broadcasts a simple advertisement for presence detection and supports a button press alert. Widely available on AliExpress/Amazon under many brand names.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFFE0` | Primary service (button notification) |
| Service UUID | `0x1802` | Immediate Alert service |
| Local name | `iTAG` | Common default name |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| iTAG present | service_uuid / local_name match | Tracker nearby |
| Button press | GATT notification on `0xFFE1` | Requires connection |

### What We Cannot Parse from Advertisements

- Battery level (requires connection to read characteristic)
- Button state (requires GATT notification subscription)
- The advertisement itself is minimal — just flags + service UUIDs + name

## Protocol Details

The iTAG is a very simple BLE peripheral:
- **Immediate Alert Service (`0x1802`)**: Write alert level to `0x2A06` to trigger buzzer
  - `0x00` = no alert, `0x01` = mild, `0x02` = high
- **Button Service (`0xFFE0`)**: Characteristic `0xFFE1` sends notification on button press
- **Battery Service (`0x180F`)**: Standard BLE battery level at `0x2A19`

## Detection Significance

- Extremely common — millions sold worldwide
- Often carried as keyfinders, pet trackers, luggage tags
- Simple presence detection is the main value for passive scanning
- Many clones use slightly different names but same service UUIDs

## References

- **Theengs decoder**: https://decoder.theengs.io/devices/iTAG.html
- **Protocol analysis**: widely documented in BLE tutorial blogs
