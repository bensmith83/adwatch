# Samsung SmartTag (SmartThings Find)

## Overview

Samsung SmartTag devices advertise using BLE service UUID `0xFD5A` as part of Samsung's SmartThings Find / Offline Finding network. This is Samsung's equivalent of Apple's Find My network.

## BLE Advertisement Format

### Identification

- **AD Type:** `0x16` (Service Data — 16-bit UUID)
- **Service UUID:** `0xFD5A` (Samsung Electronics)
- **Source:** `service_data` dictionary, key `fd5a` or full 128-bit form

### What We Know

Samsung SmartTag advertisements use Privacy IDs that:
- Rotate based on time
- Expire after 15 minutes of non-detection on helper devices
- Helper devices store up to 1000 Privacy IDs

The internal payload structure is proprietary.

### What We Don't Parse

- Privacy ID encoding
- SmartTag model (SmartTag, SmartTag+, SmartTag2)
- Battery level
- Ringing/alert state
- UWB ranging data (SmartTag+ only)

## Identity Hashing

```
identifier = SHA256("{mac}:{service_data_hex}")[:16]
```

## Detection Significance

- Indicates a Samsung SmartTag is nearby
- Samsung phones can also broadcast on `0xFD5A` when marked as lost
- SmartTag+ supports UWB for precision finding (not detectable via BLE ads)

## Limitations

- Samsung phones only become "beacons" on this UUID when explicitly marked as lost
- Not useful for general Samsung phone counting (use Company ID `0x0075` for broad Samsung detection)

## Future Work

- Reverse-engineer SmartTag payload structure from captured advertisements
- Identify Privacy ID rotation patterns
- Differentiate SmartTag models

## References

- [Samsung SmartThings Find](https://www.samsung.com/us/mobile/galaxy-smarttag/)
- [Bluetooth SIG — Service UUID 0xFD5A](https://www.bluetooth.com/specifications/assigned-numbers/) (assigned to Samsung Electronics)
