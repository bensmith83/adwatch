# Nut Tracker (BLE Keyfinder)

## Overview

Nut is a consumer BLE tracker/keyfinder brand (Nut Mini, Nut Find3, Nut Color). Similar to Tile but cheaper. Broadcasts BLE advertisements for presence detection and anti-loss alerts.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `nut*` | e.g. `nut mini`, `NUT` |
| Service UUID | Various per model | Model-dependent |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Nut device present | local_name match | Tracker nearby |
| Model type | local_name | `nut mini`, `NUT`, etc. |

### What We Cannot Parse from Advertisements

- Battery level (requires GATT connection)
- Button press events (requires GATT notification)
- Location history

## Detection Significance

- Common budget tracker, popular in Asia
- Broadcasts continuously for anti-loss
- Simple presence detection plugin

## References

- **Theengs decoder**: https://decoder.theengs.io/devices/devices.html
