# Square Reader Plugin

## Overview

**Block, Inc.** (formerly **Square, Inc.**) ships a family of mobile
point-of-sale readers under the Square brand — the **Square Reader for
contactless and chip**, the **Square Reader for magstripe**, the **Square
Terminal**, and the **Square Stand** — that pair with the Square Point of
Sale app on iOS / Android over BLE. The reader advertises before pairing so
the merchant can find it from the app and confirm a four-digit pairing code.

The contactless+chip Reader is the unit most commonly seen in the wild: it is
sold as standalone retail hardware in the United States, Canada, Japan,
Australia, the UK, France, Spain, and Ireland, and it ships in millions of
small-business deployments. All four product lines share the same BLE
fingerprint, distinguished only by the local name.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x827E` (little-endian on wire: `7e 82`) — Block, Inc. |
| Manufacturer-data sample | `7e820000000000` (CID + five zero bytes — beacon-only frame) |
| Service UUID (128-bit) | `1581EE61-0815-4B7C-B117-BED8758FEE7C` (Square reader-pairing service) |
| Local name | `"Square Reader "` + 4-digit pairing code, e.g. `"Square Reader 8765"`, `"Square Reader 9157"` |

A reader typically emits all three signals in the same advertisement, but we
match if **any** of them is present so we still classify the device when the
scanner only captured a partial advertisement (e.g. SCAN_RSP was missed).

Notes on the company identifier:

- `0x827E` (decimal 33406) is NOT currently in the public Bluetooth SIG
  company-identifier registry. Square shipped the original Reader well
  before they registered with the SIG, and the firmware kept the
  unregistered CID for backwards compatibility.
- SIG company ID `0x0AEB` is registered to "Square, Inc." and may appear in
  newer or non-Reader hardware; this parser keys on `0x827E` because that is
  what the Reader actually emits.

### Local-Name Heuristic

If the local name has the prefix `"Square Reader "` followed by a non-empty
trailing token we extract that token into `metadata["serial_suffix"]` (e.g.
`"8765"`). The local name is the stable key: `square_reader:<localName>`. We
require a non-empty trailing token so a bare `"Square Reader "` does not
false-match.

## Examples

| Capture | Inference |
|---|---|
| mfr-data `7e820000000000` + service UUID `1581EE61-…` + local name `"Square Reader 8765"` | `vendor = "Block, Inc."`, `serial_suffix = "8765"`, `device_class = payment_terminal`, stable key `square_reader:Square Reader 8765` |
| service UUID `1581EE61-…` only | matched on UUID; no `serial_suffix`; stable key falls back to MAC-derived hash |
| local name `"Square Reader 1234"` only | matched on name; `serial_suffix = "1234"` |

## References

- [Block, Inc.](https://block.xyz)
- [Square Reader for contactless and chip](https://squareup.com/us/en/hardware/contactless-chip-reader)
- [Square Terminal](https://squareup.com/us/en/hardware/terminal)
- [Bluetooth SIG Assigned Numbers — Company Identifiers](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/)
