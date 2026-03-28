# Weber iGrill Plugin

## Overview

Weber iGrill is a line of Bluetooth meat thermometers used for grilling and smoking. Models include iGrill Mini, iGrill 2, iGrill 3, and Weber Connect. They advertise over BLE for discovery and pairing, and broadcast probe temperature data.

## Supported Models

| Model | Service UUID Prefix | Probes |
|-------|-------------------|--------|
| iGrill Mini | `63C70000-4A82-4261-95FF-92CF32477861` | 1 |
| iGrill 2 | `A5C50000-F186-4BD6-97F2-7EBACBA0D708` | 4 |
| iGrill 3 | `A5C50000-F186-4BD6-97F2-7EBACBA0D708` | 4 |
| Weber Pulse 2000 | Similar to iGrill 3 | 4 |

## BLE Advertisement Format

### Identification

Weber iGrill devices can be identified by:

1. **Local Name Pattern**: Contains `iGrill` (e.g., `iGrill_mini_XXXXX`, `iGrill2_XXXXX`, `iGrill3_XXXXX`)
2. **Service UUIDs**: Model-specific UUIDs listed above

Best match strategy: `local_name_pattern=r"(?i)igrill"`.

### Advertisement Data

iGrill devices advertise their presence with:
- Local name containing model and serial
- Service UUID identifying the model generation
- Manufacturer data (limited — most data requires GATT connection)

### GATT Characteristics (for reference)

Temperature readings are available via GATT connection, not passive advertisement:

```
Probe 1: 06ef0002-2e06-4b79-9e33-fce580e36e00  (2 bytes, LE, degrees F * 10)
Probe 2: 06ef0004-2e06-4b79-9e33-fce580e36e00
Probe 3: 06ef0006-2e06-4b79-9e33-fce580e36e00
Probe 4: 06ef0008-2e06-4b79-9e33-fce580e36e00
Battery: 00002a19-0000-1000-8000-00805f9b34fb  (standard battery service)
```

Temperature value: `0xFFFF` = probe not connected, otherwise value / 10.0 = degrees Fahrenheit.

### Parser Scope (Passive Only)

Since adwatch is a passive scanner, the iGrill parser extracts:
- Device model from local_name
- Device serial/identifier from local_name suffix
- Model generation from service UUID
- Presence detection (device is powered on and advertising)

Note: Actual temperature readings require an active GATT connection. The parser documents this limitation and provides device identification/presence.

## References

- [esp32_iGrill](https://github.com/1mckenna/esp32_iGrill) — ESP32 BLE client with full protocol docs
- [esphome-igrill](https://github.com/bendikwa/esphome-igrill) — ESPHome integration
- [igrill Python library](https://github.com/bendikwa/igrill) — Original reverse engineering
