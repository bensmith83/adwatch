# Apple 0xFCB2 (Unknown Apple Service)

## Overview

Service UUID `0xFCB2` is assigned to Apple Inc. in the Bluetooth SIG assigned numbers. Its exact purpose is not publicly documented. It does not appear in the known Apple Continuity protocol (which uses manufacturer data under company ID `0x004C`).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFCB2` | Assigned to Apple Inc. |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Apple device present | service_uuid match | Apple device with unknown service nearby |

## Detection Significance

- Relatively recent UUID assignment
- May relate to Nearby Interaction, AccessorySetupKit, or an internal Apple GATT service
- Very rare in DB (part of the 6-sighting misc group)

## References

- **Bluetooth SIG Assigned Numbers**: https://www.bluetooth.com/specifications/assigned-numbers/
