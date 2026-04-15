# Polestar / Volvo Digital Key BLE Protocol

## Overview
Polestar and Volvo vehicles use BLE to implement their Digital Key system.
The car continuously advertises so the Polestar/Volvo phone app can detect
proximity and unlock/start the vehicle without taking the phone out of a
pocket.

## Manufacturer
**Polestar / Volvo Cars** — Gothenburg, Sweden. Polestar is Volvo's
performance EV brand. Both share the same digital key BLE platform.

## BLE Advertisement Structure

### Service UUIDs
| UUID | Description |
|------|-------------|
| `BF327664-CC10-9E54-5DD4-41C88FB4F257` | Proprietary digital key service |

### Local Name Patterns
| Pattern | Vehicle |
|---------|---------|
| `Polestar2` | Polestar 2 |
| `Polestar3` | Polestar 3 |
| `Polestar4` | Polestar 4 |
| `Volvo XC40` | Volvo XC40 (etc.) |

### Advertisement Behavior
- Car advertises continuously when parked and digital key is enabled
- High sighting counts (265 in 8 hours observed) — constant presence
- No manufacturer data or service data in advertisement; identification
  is purely via the 128-bit UUID and local name
- Encrypted GATT connection for actual key exchange

## Identification
- **Primary**: Service UUID `BF327664-CC10-9E54-5DD4-41C88FB4F257`
- **Secondary**: Local name matching `^(Polestar|Volvo)`
- **Device class**: `vehicle`

## Security Notes
The BLE advertisement reveals the presence and model of a nearby
Polestar/Volvo vehicle. The actual digital key protocol uses encrypted
BLE connections with challenge-response authentication. Samsung Wallet
also supports Polestar/Volvo digital keys via the same BLE interface.

## References
- Polestar Digital Key feature documentation
- Bluetooth SIG 128-bit UUID (custom, not SIG-assigned)
