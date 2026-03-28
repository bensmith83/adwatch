# Google Chromecast / Home (0xFE2C) Plugin

## Overview

Google Chromecast and Google Home devices advertise over BLE using the assigned service UUID 0xFE2C (Google LLC). This is used for device discovery and the "nearby devices" feature. These are extremely common in American households.

## BLE Advertisement Format

### Identification

Google Chromecast/Home devices can be identified by:

1. **Service UUID**: `0xFE2C` (`0000fe2c-0000-1000-8000-00805f9b34fb`)

Best match strategy: `service_uuid="fe2c"`.

### Service Data (UUID 0xFE2C)

The service data payload is typically 12 bytes:

```
Offset  Length  Field           Description
0       1       Version         Protocol version (0x00 observed)
1       1       Device Type     0x30 = Chromecast, others TBD
2-4     3       Flags/State     Device state flags
5-8     4       Device ID       Rotating device identifier
9-11    3       Extra           Additional state data
```

### Observed Patterns

All observed ads from MAC CC:19:5F:2E:FF:A3 (single device):
- Service data starts with `0030000000` consistently
- Bytes 5-8 vary (rotating identifier)
- Bytes 9-11 contain `347fe4` prefix with varying last byte
- 20+ unique ad variants, ~5.6k total sightings

### Parser Scope

The parser extracts:
- Device type byte (0x30 = Chromecast)
- Version byte
- Rotating device ID (hex)
- Service data payload for analysis

## References

- [Bluetooth SIG 0xFE2C assignment](https://www.bluetooth.com/specifications/assigned-numbers/) — assigned to Google LLC
- [Google Cast protocol](https://developers.google.com/cast)
