# EZVIZ (CID 0x01A9) — Mis-named Bead, Actually Canon

> **Naming caveat.** This bead was authored as "EZVIZ" on the assumption
> that BT SIG CID `0x01A9` belonged to EZVIZ / Hangzhou Hikvision. It does
> not. `0x01A9` is registered to **Canon Inc.**; Hangzhou Hikvision is
> `0x0E25`, and there is no EZVIZ entry in `company_identifiers.yaml` at
> all (EZVIZ products would advertise under Hikvision's CID, not this
> one). The Swift parser keeps its `EZVIZParser` symbol to preserve bead
> identity, but the parsed `vendor` and `device_class` metadata reflect
> ground truth. Every observation in our research set decodes as a
> **Canon PowerShot G7 X Mark III** compact camera; this document
> describes that protocol.
>
> If a genuine EZVIZ packet shows up later (Hikvision CID 0x0E25, or a
> different short UUID), it gets its own parser.

## Overview

Canon's recent compact-camera and DSLR lines (PowerShot G7 X Mk III,
EOS R-series mirrorless, etc.) broadcast a low-energy beacon while the
camera is powered on so the **Canon Camera Connect** smartphone app
can find the camera for transfer / remote / GPS-tag handoff. The
advertisement is purely identification: it carries a per-unit ID and
a static frame-type byte, with no live state (no battery, no shot
count, no recording status — those require GATT pairing).

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x01A9` | "Canon Inc." per SIG `company_identifiers.yaml` |
| Service UUID | `00010000-0000-1000-0000-D8492FFFA821` | Canon vendor-claimed 128-bit (the suffix `D8:49:2F` matches Canon's IEEE OUI block, confirming vendor) |
| Local name | `G7Xm3_<6 hex>` | Optional; `G7Xm3` = PowerShot G7 X Mark III; hex tail is the pairing serial used in Canon's QR / NFC handoff |
| Address type | random | Resolvable Private Address — camera rotates its BLE MAC, see "Identity Hashing" below |

The CID alone is sufficient to claim vendor (high confidence — Canon is
the SIG-registered owner of `0x01A9` with no shared-CID surprises in
the wild). The 128-bit service UUID's mid section `D8:49:2F` matches
Canon Inc.'s IEEE OUI assignment (`D8-49-2F` is a registered Canon
prefix), which is a useful secondary anchor when manufacturer data is
suppressed.

## Manufacturer-Data Layout

8 bytes, observed identical across multiple sightings of the same unit
and across two distinct units:

```
a9 01 | 01 f0 32 | XX YY | 01
└──┬─┘ └────┬───┘ └─┬──┘ └┬┘
   │        │       │     └── trailer constant (0x01 in all captures)
   │        │       └──────── per-unit ID (2 bytes, observed
   │        │                 5108 and 684b — endianness unverified)
   │        └──────────────── frame fingerprint:
   │                            byte 2  frame_version    0x01
   │                            byte 3  frame_type       0xf0
   │                            byte 4  product_family   0x32
   │                                    (also called state_byte;
   │                                    held constant across all
   │                                    captures so far)
   └──────────────────────── Canon CID 0x01A9 (little-endian)
```

The `01 f0 32` tri-byte fingerprint is identical on every G7 X Mk III
sighting we have, which makes it a reliable model-fingerprint even
when the local name is suppressed (third capture in the data set
omits the local name but its mfg-data still pins it to the same
unit and SKU).

## Local-Name Decoding

| Token | Source | Meaning |
|-------|--------|---------|
| `G7Xm3` | model prefix | PowerShot **G7 X Mark III** (Canon's compact-camera lineage: G7 → G7X → G7X Mk II → G7X Mk III) |
| `CA2680` | 6-hex serial tail | Stable per-camera token used in Canon's onboarding (matches the QR code shown on the camera's "Connect to smartphone" screen) |

We do **not** see the unit-id bytes from the manufacturer-data
(`68 4b`) encoded into the local-name suffix `CA2680` — they are
separate identifiers (different sizes, different namespaces). Treat
the mfg-data `unit_id_hex` as a coarse 16-bit token and the local-name
`serial_suffix` as the stable serial.

## Identity Hashing

```
identifier_hash = SHA256("ezviz:" + mac_address)[:16]
```

We hash on MAC rather than unit-id because:

- The unit-id field is only 2 bytes — collisions are possible across
  a population of Canon cameras.
- The local-name `serial_suffix` is **not** advertised on every
  packet (2 of 3 captures omit it).
- BLE MAC is rotating-random per Canon's RPA policy, so the hash is
  session-local; that is acceptable for our recon use case.

If a future capture set proves the `serial_suffix` is stable across
sessions and packets, we should switch identity to that token; for
now the MAC keeps us conservative.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | CID `0x01A9` | Canon Inc. (definitive) |
| Model | local-name prefix | "Canon PowerShot G7 X Mark III" when prefix is `G7Xm3` |
| Unit ID (coarse) | mfg-data bytes 5..6 | 2-byte token, possibly LE-encoded |
| Pairing serial | local-name 6-hex tail | Stable per camera, only when advertised |
| Frame fingerprint | mfg-data `01 f0 32` | Model-family signature |

## What Requires GATT or Cloud

- Battery level
- Shutter count, capture status
- Wi-Fi handoff state for image transfer
- GPS-tag handshake (the phone provides location to the camera over
  GATT — none of that is in the advertisement)
- Firmware version
- Per-image transfer state

Canon's GATT profile for Camera Connect is undocumented publicly;
community reverse-engineering exists for the *Wi-Fi* side of Camera
Connect (the JSON/Lua over HTTP API used after BLE handoff) but the
BLE GATT services themselves are not in scope here.

## Detection Significance

- **Privacy indicator** — a `G7Xm3_*` local name reveals the user is
  carrying a Canon G7 X Mk III camera (vlogger / content-creator
  preferred SKU).
- **Static fingerprint** — the `a9 01 01 f0 32 ... 01` envelope is
  identical across captures, so detection is robust even when the
  camera suppresses its local name (the camera does this between
  pairing windows; pressing the wireless button typically restores
  it).
- The camera advertises continuously while powered on; turning Wi-Fi
  off in-camera does not stop BLE.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x01A9` → "Canon Inc."
  (verified live against the SIG bitbucket mirror at
  `bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml`)
- IEEE OUI assignment `D8-49-2F` → Canon Inc. (matches the middle
  section of the vendor service UUID)
- Canon PowerShot G7 X Mark III product page — confirms the camera
  advertises BLE for Canon Camera Connect smartphone pairing
- Bluetooth SIG `Assigned_Numbers.pdf` — current snapshot of the
  company-identifiers registry
