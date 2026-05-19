# Skullcandy Plugin

## Overview

Bluetooth SIG company ID `0x07C9` is registered to Skullcandy, Inc. Their headphones / earbuds (Crusher Evo, Dime3, Crusher 540 Active, etc.) advertise this company ID alongside SIG member service UUIDs `0xFEEC` and `0xFDB3`.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x07C9` (Skullcandy, Inc.) |
| Service UUID | `0xFEEC` (Skullcandy member service) |
| Service UUID | `0xFDB3` (Skullcandy member service) |
| Local name | Friendly product name (e.g. `"Crusher Evo"`, `"Dime3_LE"`, `"Crusher 540 Active"`) |

### Manufacturer Data Layout (2 bytes after company ID)

```
Byte 0: frame type (0x00 in all observed captures)
Byte 1: product code
```

### Product Codes

| Code | Product |
|---|---|
| `0x02` | Crusher Evo |
| `0x20` | Dime3 |
| `0x31` | Crusher 540 Active |

Additional codes may appear; the parser surfaces the raw byte as `product_code` and looks the name up in a small table when known.

## References

- [Skullcandy product line](https://www.skullcandy.com/)
- [Bluetooth SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
