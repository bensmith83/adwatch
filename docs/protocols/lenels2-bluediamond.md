# Honeywell LenelS2 BlueDiamond (Access-Control Readers)

## Overview

LenelS2's **BlueDiamond** mobile-credential readers are
fixed-mount BLE+NFC access-control readers (doors, garage gates,
turnstiles, elevators) that hand off to the LenelS2 OnGuard /
NetBox backend. The product was previously branded under
Carrier's Global Access Solutions division; Honeywell acquired the
business in 2024 for ~$4.95B, taking LenelS2 (and the sibling
Onity hotel-lock line) with it.

Honeywell's own marketing copy claims **"4,000,000+ Bluetooth
locking devices deployed"** — which lines up with our corpus,
where these readers dominate the unparsed signal at over 11,000
sightings (the single largest unidentified device in our
captures).

The advertisement is **identification-only**. Credential reads,
door state, occupancy, and any link to the OnGuard / NetBox
backend live behind the reader's authenticated GATT surface and
the LenelS2 mobile-credential SDK — not extractable from passive
scans.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01F4` | "UTC Fire and Security" per SIG yaml (historical name; the registration follows the corporate lineage to Honeywell) |
| Service UUID | `0xFEA7` | Also registered to UTC Fire and Security |
| Mfg-data fingerprint | exactly 9 bytes: `f4 01 \| 01 02 ec d4 ?? 90 00` | Tight product-level signature |

CID and UUID are both registered to the same legal entity — a
very tight vendor fingerprint. The 9-byte payload format is
constant across the entire fleet except for one rolling byte;
matching that exact shape gives high-confidence product-level
identification (not just "some UTC product").

## Wire Format

```
f4 01 | 01 02 ec d4 [nonce] 90 00
 └─┬─┘ │ └──┬──┘ └──┬──┘  └─┬─┘  └─┬─┘
   │   │    │       │      │      └── constant trailer (likely ISO-7816
   │   │    │       │      │           SW1SW2 "9000" = success / online)
   │   │    │       │      └── rolling nonce / truncated rolling hash
   │   │    │       └── product sub-id 0xECD4 (BlueDiamond — constant)
   │   │    └── frame version / type 0x0102 (constant)
   │   └── CID 0x01F4 split visually for clarity
   └── company ID 0x01F4 (LE)
```

| Offset | Bytes | Field | Notes |
|--------|-------|-------|-------|
| 0-1    | `f4 01` | Company ID (LE) | UTC Fire and Security → Honeywell LenelS2 |
| 2-3    | `01 02` | Frame version / type | `0x0102` — "v1, type 2 / presence beacon" |
| 4-5    | `ec d4` | Product sub-id | `0xECD4` BE — BlueDiamond family marker |
| 6      | varies | Rolling nonce | Per-advertisement; NOT a stable per-emitter id |
| 7-8    | `90 00` | Trailer | Likely ISO-7816 status word "online/OK" |

### The rolling-nonce byte

Across our corpus, the byte at offset 6 cycles through values with
a geometric (not uniform, not monotonic) distribution. Most likely
a **truncated rolling hash** the device emits to keep iOS and
Android scanners from de-duping its broadcasts at the OS layer. Do
**not** use it as a per-emitter identifier; it changes every
advertisement.

## Identity Hashing

```
identifier_hash = SHA256(mac_address)[:16]
```

The advertisement carries no stable per-emitter id (the nonce
rotates, every other byte is fleet-constant). We rely on the BLE
MAC for identity. Each physical reader has a stable BLE MAC across
power cycles — they don't rotate like phone radios.

## Captured Examples

```
mfr= f4 01 01 02 ec d4 47 90 00
mfr= f4 01 01 02 ec d4 bf 90 00
mfr= f4 01 01 02 ec d4 21 90 00
mfr= f4 01 01 02 ec d4 4a 90 00
mfr= f4 01 01 02 ec d4 50 90 00
```

11,500+ sightings across hundreds of distinct emitters in
commercial-building captures.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID + UUID | Honeywell LenelS2 (legacy: UTC Fire and Security) |
| Product family | mfg bytes 2-5 | BlueDiamond mobile-credential reader |
| Frame type | mfg bytes 2-3 | `0x0102` |
| Rolling nonce | mfg byte 6 | Surfaced as metadata; not for identity |

## What Requires GATT / Authenticated Channel

- Mobile-credential read events
- Door open / close state
- Reader online / offline status (beyond the implicit "advertising = online")
- Cardholder identity (post-auth)
- Link to OnGuard / NetBox backend events

LenelS2 publishes a mobile-credential SDK for app developers who
need to interact with these readers, but the protocol is gated
behind a vendor agreement and is not in scope for a passive
scanner.

## Context Hint for the UI

Seeing several BlueDiamond readers clustered is a strong signal
that you're inside a commercial building with electronic access
control — typical environments are office lobbies, parking
garages, university buildings, hospitals, and gym/fitness chains.
A single reader nearby usually marks a door, gate, or elevator
checkpoint.

## Why "UTC Fire and Security" Still Shows in the SIG

The SIG company-id registration has not been re-issued since the
2024 Honeywell acquisition. The SIG yaml still says:

```yaml
- value: 0x01F4
  name: 'UTC Fire and Security'
```

The same legal entity now operates under Honeywell. We surface
both names in metadata (`vendor` and `vendor_legacy`) so future
re-registration changes don't break analysts looking for the older
label.

## References

- [Bluetooth SIG `company_identifiers.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x01F4` → "UTC Fire and Security"
- [Bluetooth SIG `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFEA7` → "UTC Fire and Security"
- [Honeywell LenelS2 BlueDiamond product page](https://buildings.honeywell.com/us/en/brands/our-brands/lenels2/security-products/blue-diamond)
- Honeywell completes acquisition of Carrier Global Access Solutions (2024)
- [Nordic `bluetooth-numbers-database`](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — corroborates `0x01F4` company name
