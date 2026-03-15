# BM2 Car Battery Monitor — 12V Battery Voltage

## Overview

BM2 is a clamp-on 12V car battery monitor that broadcasts battery voltage via BLE. Sold under many brands: BM2, Quicklynks, Leagend, Battery Monitor. The protocol uses AES-128 CBC encryption, but the key is static and publicly known.

## Identification

- **Local name:** `Battery Monitor` or `ZX-1689`
- **Service UUID:** `0xFFF0`

## Advertisement Format

The voltage data is AES-128 CBC encrypted in the manufacturer-specific data or service data.

### Decryption

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = b'leagend\xff\xfe188246\x00\x00\x00'  # 16 bytes, null-padded
IV = b'\x00' * 16  # all zeros

cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV))
decryptor = cipher.decryptor()
plaintext = decryptor.update(encrypted_data) + decryptor.finalize()
```

### Decrypted Payload (16 bytes)

| Offset | Size | Field | Encoding |
|--------|------|-------|----------|
| 0 | 1 | Header | uint8 — message type |
| 1-2 | 2 | Voltage raw | uint16 BE — `(value >> 4) / 100.0` = volts |
| 3-15 | 13 | Unknown | Padding / reserved |

### Voltage Calculation

```python
raw = (plaintext[1] << 8) | plaintext[2]
voltage = (raw >> 4) / 100.0  # e.g., 1232 >> 4 = 77 ... 12.32V
```

Typical values: 11.5V - 14.8V (12V lead-acid battery range)

## ParseResult Fields

- `voltage` (float): Battery voltage in volts
- `encrypted` (bool): Always True (for metadata)

## Notes

- Requires `cryptography` package for AES decryption
- The static key means any BM2 device can be read by any receiver
- Device advertises frequently (~1 second interval)

## References

- https://haxrob.net/bm2-reversing-the-ble-protocol-of-the-bm2-battery-monitor/
