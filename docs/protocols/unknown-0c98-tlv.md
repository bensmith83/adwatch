# Unknown TLV Beacon Family — Vanity Company ID `0x0C98`

## Overview

A previously-uncatalogued BLE device family advertising manufacturer data
under company ID **`0x0C98`** (on-air little-endian `98 0c`). The CID is
**not** present in the Bluetooth SIG `company_identifiers.yaml` assignment
list — it is a vanity / unregistered identifier and tells us nothing about
the vendor on its own.

The **structure is solved**: the manufacturer payload (the bytes after the
2-byte CID) is a clean, self-consistent **type-length-value (TLV) stream**.
The **vendor is not** — the CID is unregistered and every captured payload is
almost entirely idle (zeros), so there is no labelled or non-idle specimen to
attribute it to. The family is catalogued here as `vendor: Unknown` with a
**structural, unattributed** parser whose job is to count/group the emitter
and pin a stable per-device id. Revisit when a non-idle or labelled capture
appears.

## Fingerprint

### Company ID

| CID | Status |
|-----|--------|
| `0x0C98` (LE `98 0c`) | Not SIG-registered — vanity / unregistered |

### Payload is a TLV stream

The payload after the CID is a repeating sequence of records:

```
<tag: 1 byte><len: 1 byte><value: len bytes>
```

The decisive, precise signal is that this walk consumes the buffer
**exactly** — every observed frame ends on a record boundary with zero
leftover bytes and no length that overruns the buffer. That self-consistency
across all six captured frames is the evidence the format is a genuine TLV
layout rather than a coincidence, and it doubles as the parser gate: a
random/garbage `0x0C98` payload that does not walk cleanly is rejected
(returns no result).

### Observed captures

Six devices from `nearsight_export 7.json`. Manufacturer data shown including
the 2-byte CID:

```
980c010861048c4748110300                              (1 rec:  01)
980c08020000090200000b01000d01000c020000040410001005  (6 recs: 08 09 0b 0d 0c 04)
980c060800a0c72b47dd4317070809000000000000000a0100    (3 recs: 06 07 0a)
980c0e04000000000f01001009000000000000000000          (3 recs: 0e 0f 10)
980c0208e61a38030000000003010c05040e00010100020700    (4 recs: 02 03 05 00)
980c0208e11a38030000000003010c05040e00010100020700    (4 recs: 02 03 05 00)
```

### Observed tags and lengths

| Tag | Value length | Notes |
|-----|--------------|-------|
| `00` | 2 B | semantics unknown |
| `01` | 8 B | per-frame value; used as fallback device id |
| `02` | 8 B | **per-device id** (see below) |
| `03` `0a` `0b` `0d` `0f` | 1 B | semantics unknown (mostly idle) |
| `04` `05` `0e` | 4 B | semantics unknown (mostly idle) |
| `06` `07` | 8 B | semantics unknown |
| `08` `09` `0c` | 2 B | semantics unknown |
| `10` | 9 B | semantics unknown |

The semantics of the values are **unknown** — most are idle zeros. We do not
invent or decode meaning.

### Tag `0x02` is the per-device id

The last two frames are byte-for-byte identical **except** for tag `0x02`'s
value (`e61a3803…` vs `e11a3803…`). That isolates tag `0x02` as the per-unit
identifier, so we surface it as the stable identity anchor.

## Identification

- **Primary**: company ID `0x0C98` **and** a payload that parses as a valid
  TLV stream (walks exactly to end-of-buffer, ≥ 1 record).
- **Device class**: `unknown` — this is a structural, unattributed parser.

## What We Can Surface

| Field | Source | Notes |
|-------|--------|-------|
| `vendor` | hard-coded | `Unknown` — CID unregistered, no labelled specimen |
| `company_id` | CID | `0x0c98` |
| `sig_id_status` | hard-coded | `non_sig_vanity` |
| `tlv_tags` | TLV walk | comma-joined 2-hex tags in order (e.g. `02,03,05,00`) |
| `tlv_record_count` | TLV walk | number of records |
| `device_id_hex` | tag `0x02`, else tag `0x01` | per-device id hex, when present |

## What We Cannot Surface

- Vendor / brand / product class — the CID is unregistered and no labelled
  specimen exists.
- Semantics of any tag's value — the payloads observed so far are almost
  entirely idle, so no field meaning can be inferred honestly.

## Stable Identity

```
stable_key = unknown_0c98_tlv:<device_id_hex>   (tag 0x02 present, else tag 0x01)
stable_key = unknown_0c98_tlv:mac:<mac>         (no id tag present)
identifier = SHA256(stable_key)[:16]
```

Tag `0x02` (or, as a fallback, tag `0x01`) gives a per-unit id that is
independent of the rotating BLE MAC. Frames with neither id tag fall back to
the MAC, which will not survive random-address rotation — acceptable for a
fingerprint-only catalogue entry until richer captures arrive.

## Detection Significance

- Lets us count and group an otherwise-uncatalogued beacon family instead of
  dropping it as an unknown `0x0C98` blob.
- The walk-to-end TLV gate keeps precision high: it claims only payloads that
  are structurally the real format, not every frame that happens to carry CID
  `0x0C98`.

## Revisit When

- A frame with non-idle (non-zero) tag values is captured — may let us infer
  field semantics.
- A labelled / ground-truth specimen turns up (active scan name, GATT Device
  Information Service, FCC ID, or packaging) — would let us attribute the
  vendor and upgrade `vendor: Unknown`.

## References

- Bluetooth SIG company_identifiers.yaml (no `0x0C98` entry — confirms vanity
  status) —
  <https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml>
- Captures: `research/nearsight_export 7.json` (6 devices).
- Companion unattributed / fingerprint-only parsers in this codebase:
  - `Unknown65333333Parser` — vanity-UUID family, vendor catalogued as Unknown
  - `VendorNode2A2AE2DBCCE4Parser` — UUID-v1 node cluster, vendor Unknown
