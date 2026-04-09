# Dexcom CGM BLE Protocol

## Overview
Dexcom Continuous Glucose Monitors (CGM) are medical devices worn on the body
that measure interstitial glucose levels and transmit readings via BLE every
5 minutes. Models include G6, G7, and Dexcom ONE.

## Manufacturer
**Dexcom, Inc.** — San Diego, CA. Major medical device company specializing
in continuous glucose monitoring for diabetes management.

## BLE Advertisement Structure

### Service UUIDs
| UUID | Description |
|------|-------------|
| `61CE1C20-E8BC-4287-91FD-7CC25F0DF500` | Dexcom proprietary CGM data service |
| `180A` | Standard Device Information Service |

### Local Name Patterns
| Pattern | Model |
|---------|-------|
| `DEX` | G7 / Dexcom ONE (short name) |
| `DexcomXX` | G6 (suffix from transmitter serial) |

### Advertisement Behavior
- Advertises continuously while sensor session is active (10-day G6, 10-day G7)
- BLE 4.0+ Low Energy
- Uses encrypted GATT connection for glucose data transfer (HIPAA-sensitive)
- Advertisement alone reveals device presence but not glucose readings

## Identification
- **Primary**: Proprietary service UUID `61CE1C20-E8BC-4287-91FD-7CC25F0DF500`
- **Secondary**: Local name matching `^(DEX|Dexcom)`
- **Device class**: `medical`

## Privacy Notes
CGM devices transmit health-related data. The BLE advertisement itself does not
contain glucose readings (those require an encrypted paired connection), but the
presence of a Dexcom transmitter reveals that someone nearby uses a CGM.

## References
- xDrip+ open-source CGM receiver: reverse-engineered GATT characteristics
- Dexcom developer portal (limited public documentation)
- Bluetooth SIG Device Information Service (0x180A)
