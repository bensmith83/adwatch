# Clover Payment Terminal BLE Protocol

## Overview

Clover POS (Point-of-Sale) payment terminals by Fiserv advertise via BLE using company ID 0x7103. These are commonly found in retail stores, restaurants, and service businesses. The advertisement contains device identification including an ASCII serial number.

## Identifiers

- **Company ID:** `0x0371` (Fiserv/Clover — bytes `71 03` little-endian)
- **Local name pattern:** `CC{model}{serial}` (e.g., `CCJB621450531`)
- **Device class:** `payment_terminal`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x7103` | Fiserv/Clover registered ID |
| Local name | `CC{model}{serial}` | "CC" prefix = Clover Commerce |

### Manufacturer Data Structure

Variable length (2 company ID + 2+ header + optional serial)

#### Examples

```
71 03 01 04 62 00 02 00 4a 42 48 55 33 34 36 34 32 37   (full, with serial)
71 03 01 04 4b 00                                         (short, no serial)
71 03 01 04 62 00                                         (short variant)
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `71 03` | Company ID 0x7103 (little-endian) |
| 2 | 1 | `01` | Protocol version |
| 3 | 1 | `04` | Device type/flags |
| 4 | 1 | `62`/`4b` | Model identifier byte |
| 5 | 1 | `00` | Padding/reserved |
| 6-7 | 2 | `02 00` | Extended header (when serial follows) |
| 8+ | var | ASCII | Device serial number (e.g., "JBHU3464227") |

### Local Name Format

| Example | Prefix | Model | Serial |
|---------|--------|-------|--------|
| `CCJB621450531` | CC | JB | 621450531 |
| `CCGB616512155` | CC | GB | 616512155 |

Known model codes:
- **JB** — Clover Flex (handheld terminal)
- **GB** — Clover Go (mobile card reader)

### Serial Number in Manufacturer Data

The ASCII serial embedded in manufacturer data (e.g., "JBHU3464227") is Clover's internal hardware serial, distinct from the numeric serial in the local name. This is notable from a security/privacy perspective — the serial is broadcast in plaintext.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | company_id | Clover terminal nearby |
| Model code | local_name[2:4] | Terminal model type |
| Local serial | local_name[4:] | Numeric serial number |
| Hardware serial | mfr_data ASCII | Internal serial (when present) |
| Protocol version | mfr_data byte 2 | Currently `01` |

### What We Cannot Parse (requires payment network connection)

- Transaction data
- Merchant information
- Payment status
- Terminal configuration

## Identity Hashing

```
identifier = SHA256("clover:{mac}")[:16]
```

## Detection Significance

- Indicates proximity to a retail checkout or payment processing area
- Multiple Clover terminals = busy retail environment
- Model codes indicate business type (Flex for restaurants, Go for mobile vendors)

## References

- [Clover](https://www.clover.com/) — Fiserv POS platform
- Company ID 0x7103 registered to Fiserv/Clover
