# PayRange BluKey Plugin

## Overview

[PayRange Inc.](https://payrange.com/) makes the **BluKey** family of BLE inline modules — small dongles retrofitted into vending machines, laundromats, parking meters, and amusement machines so customers can pay by phone via the PayRange app. Each module advertises continuously with a 16-bit Bluetooth SIG company ID of `0x02C9` and a `local_name` of `"PR"`.

The advertisement broadcasts two useful fields for asset inventory and surveying:

1. A **stable 32-bit serial number** that identifies the physical BluKey unit across reboots and MAC rotations.
2. An optional **16-byte operator-assigned machine label** carried in an extended ad frame. Operators routinely set labels like `"Coke 8th Flr co"`, `"Snack 8th Flr c"`, `"Coke 9th Flr co"` — i.e. friendly names that geolocate the unit inside a building.

This is a **non-payment-related** read of public, unauthenticated advertising data; no payment, card, or user identifier is exposed.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x02C9` | Registered to PayRange Inc. in the Bluetooth SIG. |
| Local name | `"PR"` | Constant across the fleet. |

The Bluetooth SIG company-identifier registry lists `0x02C9 = PayRange Inc.` ([Bluetooth SIG assigned numbers](https://www.bluetooth.com/specifications/assigned-numbers/), [YAML mirror](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)).

### Manufacturer Data Layout

Two frame shapes are observed; the first 14 bytes are identical.

#### Heartbeat (short) form — 14 bytes after company ID

```
Byte 0      : 0x00                — record version / type (constant)
Bytes 1..4  : SS SS SS SS         — 32-bit unit serial, little-endian (stable per device)
Bytes 5..8  : NN NN NN NN         — opaque rolling nonce / auth tag (changes every advertisement)
Bytes 9..10 : 08 08                — constant flags (purpose unconfirmed)
Bytes 11..13: 5b 02 00            — constant protocol-version / model tag
```

#### Labeled (extended) form — 41 bytes after company ID

The first 14 bytes are identical to the heartbeat form, then:

```
Bytes 14..23: 01 01 00 00 00 00 00 02 00 00   — status TLV header (all-zero status observed)
Byte 24     : 0x24                              — label tag
Bytes 25..40: LL LL ... LL 00                  — 16-byte NUL-padded ASCII machine label
```

A given BluKey alternates between the short heartbeat (frequent) and the longer labeled form (less frequent). Several physical machines were only ever observed in the heartbeat form during the 24h capture window, suggesting label broadcast may be configurable, throttled, or disabled when the operator hasn't set a label.

### Serial Decoding

Bytes 1..4 of the manufacturer payload form a little-endian unsigned 32-bit serial number. This is the **stable identity** of the physical BluKey across MAC rotations and reboots — it is the right field to use as the device's primary key.

| Bytes (LE) | Serial (decimal) | Observed label |
|---|---:|---|
| `be f4 d5 00` | 14,021,822 | "Coke 8th Flr co" |
| `1a f4 d5 00` | 14,021,658 | "Snack 8th Flr c" |
| `d3 eb d5 00` | 14,019,539 | "Coke 9th Flr co" |
| `7a ff d5 00` | 14,024,570 | (heartbeat only) |
| `3c 0d d6 00` | 14,028,092 | (heartbeat only) |

### Nonce / Auth Tag

Bytes 5..8 vary on every advertisement of the same BluKey, with no ordering or pattern visible across thousands of consecutive sightings. The bytes look uniformly distributed and are almost certainly a rolling nonce or HMAC tag used by the PayRange app during pairing/handshake, validated server-side. We surface them as `nonce_hex` for debugging but treat them as opaque — **do not** use them as an identifier (they change every advertisement) and do not infer a counter from them (they are not monotonic).

A prior reverse-engineering effort against an earlier BluKey generation (which broadcast under BlueRadios SIG ID `0x0085` rather than under PayRange's own `0x02C9`) is documented at [Osmophile — Reverse Engineering the PayRange BluKey Protocol](https://www.osmophile.com/payrange1/) and is a useful reference if anyone wants to push further into this field's semantics.

### Machine Label

When present, the operator-assigned machine label is a NUL-terminated ASCII string in a fixed 16-byte field starting at payload offset 25. The string is truncated by the operator dashboard at 16 bytes — that's why captures show labels like `"Coke 8th Flr co"` (which is almost certainly the full name `"Coke 8th Flr coffee corner"` or similar, hard-truncated at byte 16).

The parser surfaces the label as `metadata["label"]` after stripping NUL padding and validating that all bytes are printable ASCII.

## Detection Significance

- **Common in commercial buildings.** PayRange has retrofits across hundreds of thousands of vending machines, laundromats, and amusement venues. Office buildings with a cafeteria stack are a particularly dense capture environment (we saw 6 distinct units in a single 24h window).
- **Workplace location leakage.** The label field broadcasts plaintext machine names that geolocate to specific floors. A passive scanner in the lobby can enumerate the cafeteria layout of a tenant company. This is a real privacy property of the protocol — not a parser implementation choice.
- **Stable physical asset ID.** The 32-bit serial is broadcast continuously and persists across BLE address rotations, so the unit is trackable by serial number. From an asset-inventory perspective this is useful; from a privacy perspective it means the unit's location can be re-identified from any nearby scan.
- **No payment data leaks.** PayRange's payment flow is cloud-mediated; the advertisement carries no card data, transaction state, or user identity.

## Privacy & Security Notes

- We display the label in the device detail view because it is the most informative field, but operators should be aware that PayRange's default behavior **broadcasts the machine's friendly name in plaintext to anyone in range**.
- The 32-bit serial enables physical-asset tracking — pair this with location services and you can map the fleet of any building with a PayRange deployment.
- The nonce/auth tag in bytes 5..8 looks like an anti-replay token for app-initiated payment sessions; further investigation is outside the scope of this parser.
