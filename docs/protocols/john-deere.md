# John Deere equipment PIN beacon (CID 0x0606)

## Overview

**John Deere** (Deere & Company) holds Bluetooth SIG company identifier
`0x0606` and the SIG member service UUID `0xFE25`. Its connected
equipment — JDLink telematics gateways, machine display/receiver
modules, and the Bluetooth radios on newer compact and utility tractors
that the Operations Center / "Deere" mobile apps pair with — advertise
over BLE.

The frame documented here is a **manufacturer-data beacon under CID
`0x0606` whose entire payload is the machine's 17-character product
identification number (PIN) in plaintext ASCII**. A passive scanner that
sees one of these knows the make, the model and the unit's serial
number of a piece of Deere equipment in radio range.

First captured 2026-08-24 (nightly sweep): one unit, 37 sightings inside
a 49-second window at −88..−100 dBm, random address, no local name. The
PIN decoded to a current compact-utility-tractor model built at the
plant its manufacturer code points to — two payload facts that
corroborate the company ID independently of each other.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0606` (LE wire `06 06`) | SIG-assigned to *John Deere* — unique and uncollidable |
| Payload | 17 bytes of printable ASCII in the Deere PIN grammar | Second, independent vendor signal (manufacturer code + model) |
| Service UUID | `9E110100-C035-45ED-B09C-20FA58217A2A` | Vendor 128-bit UUID advertised alongside; not in any registry we hold; bytes are not ASCII |
| Address type | random | Rotates; identity anchors on the PIN, not the address |
| Device class | `vehicle` | Agricultural / turf equipment is treated as a vehicle |

`0xFE25` (John Deere's SIG member UUID) was seen in the same corpus as a
separate 13-byte service-data frame (`06 20 8d 82 55 58 64 39 48 00 d0 08
00`, one sighting at −100 dBm). It is **not** claimed by this parser —
different device, unknown structure; recorded as a watch item.

## Ad Format

Manufacturer data, 19 bytes including the company ID:

```
offset  0  1 | 2  3  4 | 5  6  7  8  9 | 10 11 12 | 13 14 15 16 17 18
        06 06 | 31 4c 56 | 32 30 32 35 52 | 54 54 54 | dd dd dd dd dd dd
        CID     "1LV"      "2025R"          "TTT"      6-digit serial
```

Payload positions (offset from the start of the PIN):

| PIN chars | Field | Observed | Notes |
|-----------|-------|----------|-------|
| 1–3 | manufacturer / plant code | `1LV` | Deere's world-manufacturer code for the Augusta, GA works, which builds the 1–4 series compact utility tractors |
| 4–8 | model | `2025R` | John Deere 2025R compact utility tractor |
| 9–11 | code letters | `TTT` | Deere's commonly cited 17-character layout puts a check letter, a model-year letter and a plant letter here. Under that layout the model-year `T` would read as 2026, consistent with a current-production unit seen in August 2026 — **not verified** at n=1, so the parser reports the three letters raw |
| 12–17 | serial | six digits | Per-unit; the parser's identity key |

The full 17-character string is the PIN stamped on the machine's
identification plate. The capture's serial digits are deliberately not
reproduced in this document or in the app's test fixtures.

### Parser gate

The parser claims a frame only when **all** of:

1. company ID is `0x0606`;
2. the payload is exactly 17 bytes;
3. every byte is an ASCII digit or upper-case letter;
4. the last six bytes are digits.

Anything else under `0x0606` is left unclaimed (honest-unknown) rather
than force-decoded — a JDLink gateway or display module that advertises a
different `0x0606` frame will show up as an unparsed `0x0606` record for
a future sweep.

## Identity Hashing

The BLE address is random and rotates, and the PIN is a permanent
per-unit identifier, so identity anchors on the PIN:

```
identifier = SHA256("john_deere:{pin}")[:16]
stableKey  = "john_deere:{pin}"
```

`pin` and `pin_serial` are tagged `uniqueStable` (kept off the telemetry
wire); `model` is tagged `modelIdentifying`.

## Parser Scope

Passive only. The parser does not connect, does not read GATT, and does
not interpret the 128-bit service UUID beyond surfacing it. No machine
state (hours, fuel, position, implement) is present in this frame.

## Detection Significance

A sighting means **a specific piece of John Deere equipment, identified
to the serial number, is within BLE range** — a farm, dealer lot,
municipal yard, golf course or a neighbour's tractor. Because the PIN is
the same number used for registration, warranty and theft reporting,
this is one of the more identifying passive beacons in the catalogue,
comparable to a vehicle broadcasting its VIN.

## Confidence / Attribution

**Vendor: high.** Two independent signals — the SIG company ID assigned
to John Deere, and a payload that is a well-formed Deere PIN whose
manufacturer code and model agree with each other (Augusta builds the
2025R).

**Product: medium.** The PIN says which *machine* the beacon belongs to;
it does not say which Deere module inside it (factory Bluetooth on the
tractor, a JDLink gateway, a retrofit receiver) is transmitting.

**Breadth: low — one unit, one day.** The gate is strict enough (CID +
PIN grammar) that a second unit will confirm or falsify it without any
risk of over-claiming in the meantime. Revisit when a second PIN or a
non-PIN `0x0606` frame appears.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x0606 = John Deere`.
- Bluetooth SIG `member_uuids.yaml` — `0xFE25 = John Deere`.
- NearSight `research/sweep-2026-08-24-candidates.md` — capture evidence
  and the rejected/deferred siblings from the same corpus.
