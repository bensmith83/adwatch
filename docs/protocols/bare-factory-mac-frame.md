# Bare Factory-MAC Manufacturer Frame

## Overview

Not a product — a **wire-format pattern**. Some BLE devices fill the entire
AD type `0xFF` (manufacturer specific data) field with their 48-bit factory
MAC address followed by two zero bytes, and put no company identifier in it
at all.

That matters more than it sounds, because every BLE stack LE-decodes the
first two bytes of an `0xFF` field as a company ID. So these frames arrive
looking like company IDs `0x8D38`, `0x2E28`, `0x53D4`, `0x0E88` — none of
which are SIG-assigned — when in reality those bytes are the first two
octets of the vendor's OUI. A parser keyed on such a "company ID" is really
keyed on one OUI block, and will mis-group every sibling block the same
vendor owns.

Discovered in the NearSight 2026-08-07 telemetry sweep.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Frame length | exactly 8 bytes | 6-byte MAC + `00 00` |
| Bytes 6–7 | `00 00` | the structural tell |
| Byte 0, bits 0–1 | both clear | globally-unique unicast MAC |
| Bytes 0–2 | a registered IEEE MA-L OUI | the identification signal |
| Company ID | **none present** | bytes 0–1 are MAC octets |
| Address type | random | on every observed unit |

## Ad Format

```
 0  1  2 | 3  4  5 | 6  7
oo oo oo | nn nn nn | 00 00
  OUI      NIC       zero tail
└──────── 48-bit factory MAC ────────┘
```

## Observed Instances

| Frame | Decoded MAC | IEEE MA-L owner | Units |
|-------|-------------|-----------------|-------|
| `388d3df102ae0000` | `38:8D:3D:F1:02:AE` | WNC Corporation (Wistron NeWeb) | 5 |
| `282e895a98b60000` | `28:2E:89:5A:98:B6` | WNC Corporation (Wistron NeWeb) | 4 |
| `d453834e6ff70000` | `D4:53:83:4E:6F:F7` | Murata Manufacturing Co., Ltd. | 1 |
| `3409c92632ae0000` | `34:09:C9:26:32:AE` | Dongguan Huayin Electronic Technology | 3 |
| `880e8582a2de0000` | `88:0E:85:82:A2:DE` | Shenzhen Boomtech Industrial | 1 |
| `984744a21f220000` | `98:47:44:A2:1F:22` | Shenzhen Boomtech Industrial | 1 |

The last three rows also advertise a truncated 32-bit vendor service UUID
of the form `DAF5xxxx`; the WNC and Murata units advertise no service UUID
and no local name at all.

## How the pattern was confirmed

The claim "these six bytes are a MAC" is falsifiable, and was tested against
the whole corpus rather than argued from appearance.

Of all 8-byte manufacturer payloads in the corpus whose last two bytes are
`00 00`, **6 of 18** distinct 3-byte prefixes resolve to a registered IEEE
MA-L block:

| | rate |
|---|---|
| observed, `00 00` tail | **33.3%** (6 / 18) |
| observed, non-`00 00` tail (control) | 3.5% (3 / 86) |
| expected for random 3-byte values | **0.24%** (39,902 assignments / 2^24) |

That is a ~139× enrichment over base rate; the binomial probability of it
arising by chance is ~1e-13. Two supporting checks:

- **All six** have the multicast (bit 0) and locally-administered (bit 1)
  bits of byte 0 clear — i.e. all six are valid globally-unique factory MAC
  prefixes. Random bytes would satisfy that only 25% of the time.
- **Two of the six blocks belong to the same vendor** (`88:0E:85` and
  `98:47:44`, both Shenzhen Boomtech). A random-byte explanation has no
  reason to produce two blocks of one company.

The control group's only three "hits" are the low-numbered legacy blocks
`00:00:12`, `00:00:28` and `00:00:78` — exactly what zero-padded payloads
collide with by accident, which is the expected shape of the null result.

## Parser Scope (Passive Only)

The parser reports the decoded MAC, the OUI, the IEEE registry owner of
that OUI, and the pseudo-company-ID the frame *appears* to carry (flagged
`company_id_status: not_a_company_id`).

**Identity:** anchored on the embedded MAC. This is both the honest key and
a real improvement — it is stable across BLE address rotation, where the
live address is not.

**Vendor is reported as `Unknown`.** The OUI owner is recorded separately
as a registry fact, not as an attribution: WNC, Murata, Huayin and Boomtech
are ODM / module houses, so the OUI identifies the silicon or the
contract manufacturer, not the retail product.

**Coverage requires two edits, not one.** Because routing keys are wire
bytes 0–1, teaching the OUI lookup about a new block is not enough — that
block's pseudo-CID must also be added to the parser's routing registration.
This coupling is a known wart and the main argument for consolidating the
family (below).

## Privacy Significance

Every observed unit advertises a **random** (private) BLE address while
broadcasting its **permanent factory MAC in the clear**. The address
rotation therefore provides no privacy whatsoever: anyone in range can
re-identify the device indefinitely, and on Wi-Fi-capable silicon the same
MAC is often the device's Wi-Fi identity too.

This is the same design failure documented for the Afero platform (see
`afero-platform-device.md`) — and worth flagging in any audit of a
deployment using these modules.

## What We Cannot Parse

- Vendor brand, retail product, or device class
- Firmware version, state, sensor readings — the frame carries none
- Why the `00 00` tail exists (length padding vs. a reserved field)

## Relationship to the `DAF5*` family

The `DAF5xxxx`-advertising devices are the same grammar. All six `DAF5`
records in the corpus are 8-byte `<6-byte MAC><00 00>` frames, and three of
their four OUI prefixes are IEEE-registered.

Those six devices are presently split across **five separately-named
parsers** in NearSight, each named after two bytes that are a MAC's first
two octets rather than a company ID — and two of those names no longer even
describe the fixture they catch, because they actually match on the service
UUID. Consolidating them onto this grammar is filed as follow-up work.

The historical `cid_0e88_cluster` is the cautionary example: it is keyed on
"CID `0x0E88`", which is really `88:0E:…`, the first two bytes of one of
Shenzhen Boomtech's two OUI blocks. It nonetheless catches a `98:47:44`
Boomtech unit — whose "CID" would be `0x4798` — only because it also
matches the service UUID. That parser had already had a vendor attribution
retracted once; the deeper problem was that the identifier it was named for
never existed.

## Confidence / Attribution

**HIGH on the wire format** — the statistics above are decisive, and the
same-vendor-two-blocks coincidence is independent corroboration.

**NO product attribution, deliberately.** The OUI tells us whose silicon or
whose contract manufacturing is inside; it does not tell us what the device
is or whose logo is on it.

## References

- [IEEE MA-L registry (`oui.csv`)](https://standards-oui.ieee.org/oui/oui.csv)
  — fetched 2026-08-07; all OUI resolutions above grepped locally
- Bluetooth SIG `company_identifiers.yaml` — `0x8D38`, `0x2E28`, `0x53D4`
  and `0x0E88` all absent, consistent with "not a company ID"
- `afero-platform-device.md` — the same random-address / MAC-in-the-clear
  privacy failure, on a different platform
- NearSight `Sources/Parsers/BareFactoryMACFrameParser.swift`,
  `Sources/Parsers/OUIVendorLookup.swift`
