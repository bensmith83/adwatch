# Samsung TV / Soundbar BLE Protocol

## Overview

Samsung TVs and soundbars broadcast BLE advertisements using Samsung's company ID. The manufacturer data contains device type information, and named advertisements include the TV model.

## Identifiers

- **Company ID:** `0x0075` (Samsung Electronics Co. Ltd.)
- **Local name patterns:** `[TV] *`, `[AV] *`, `*Crystal UHD*`, `*The Frame*`, `*Samsung*`
- **Device class:** `tv`, `soundbar`, `display`

## "The Frame" (art-mode TV line) — name recognition (2026-07-06)

Samsung's **The Frame** TVs advertise under CID `0x0075` with manufacturer
**type bytes `0218`** and a self-identifying local name `<size>" The Frame`
(e.g. `65" The Frame`). They are matched **by the localName substring
`The Frame`, never by the manufacturer bytes** — see the warning below.

| Field | Value |
|---|---|
| Match rule | `localName` contains `The Frame` (full substring) |
| `product_line` | `The Frame` |
| `model` | the raw local name (e.g. `65" The Frame`) |
| `screen_size_inches` | parsed from the leading `NN"` (e.g. `65`) |
| Device class | `tv` |

**Why not the `0218` type byte.** In one live corpus, **123 records** started
`7500 0218`, spanning Crystal UHD sets, SmartThings appliances, and other TVs;
even the deeper sub-type `0218 34a1` is emitted by both a Frame and a
`65" Crystal UHD`. No manufacturer byte distinguishes the model — matching
`0218` (or `0218 34a1`) would misclassify those other models as The Frame.
The full `The Frame` name substring is the only false-positive-safe
discriminator (a bare `Frame` is intentionally *not* matched). A Frame TV
also emits a `4204` frame that this parser already recognizes; when the name
is present the `product_line`/`screen_size_inches` enrichment applies to
either frame, and the nameless `0218` sibling frame is deliberately left
unparsed.

## Manufacturer Data Format

24 bytes total (after company ID prefix in raw BLE):

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 | Company ID | `0x0075` (LE: `7500`) |
| 2-3 | 2 | Type/subtype | `0x4204` common for TVs, `0x0218` for another variant |
| 4 | 1 | Flags/mode | Varies: `01`, `83`, etc. |
| 5 | 1 | Sub-flags | `80`, `40`, `01` observed |
| 6-23 | 18 | Payload | Device-specific, includes repeated patterns |

### Observed Type Bytes

- `4204` — Most common. Seen on all named TVs and unnamed Samsung ads. Fixed 24-byte payload with repeated 6-byte blocks at offsets 6-11 and 12-17.
- `0218` — Secondary format. 32-byte payload. Different internal structure, possibly newer firmware.

## Sample Advertisements

### Named TVs (type 0x4204)
```
[TV] UN75JU641D:       750042040101ae14bb6eb39bd616bb6eb39bd501000000000000
[TV] Samsung Q6DAA 75: 75004204012067210f0022014b01010001000000000000000004
[AV] Samsung N850:     (similar structure)
75" Crystal UHD:       75004204018060d003dfbb3ff5d203dfbb3ff401000000000000
```

### Unnamed (type 0x0218)
```
7500021844a113aee3055c03e6882b2275f2768c47852740477d
7500021861a11ea7555e0e838550ad853cdec924057b7e6f7701f00bb856c247
```

## Parsing Strategy

1. Match on company_id `0x0075`
2. Extract type bytes at offset 2-3
3. For type `0x4204`: extract flags at offset 4-5, note the 6-byte repeated blocks
4. Extract model name from local_name if present (strip `[TV]`/`[AV]` prefix)
5. Classify as tv/soundbar/display based on local_name prefix

## Device Classification

| Name Pattern | Device Class |
|-------------|-------------|
| `[TV] *` | tv |
| `[AV] *` | soundbar |
| `*Crystal UHD*` | tv |
| `*The Frame*` | tv (`product_line = The Frame`) |
| No name | unknown_samsung |

## References

- Bluetooth SIG Company ID `0x0075` — Samsung Electronics
- Samsung SmartThings BLE integration
- No official protocol documentation — reverse engineered from advertisement captures
