# Unknown `0x6C14` + `DAF58A01-…` BLE Device Plugin

## Overview

A BLE device observed in the 2026-07-06 live telemetry sweep advertising two
signals that no public source attributes to a specific product:

1. **Manufacturer data CID `0x6C14`** — in the company-identifier slot. `0x6C14`
   (27668 decimal) is far above the SIG company-identifier ceiling (max
   assigned ≈ `0x10E1`), so it is **not** a SIG-assigned Company Identifier —
   a vanity/unregistered choice.
2. **Custom 128-bit service UUID with prefix `DAF58A01`** — fully custom; not
   in the SIG `service_uuids.yaml` / `member_uuids.yaml` and not in
   `NordicSemiconductor/bluetooth-numbers-database`.

**Sibling of [`unknown-fe7c-daf58e01.md`](unknown-fe7c-daf58e01.md).** That
device advertised `7cfe624bb73c0000` (CID `0xFE7C`) with serviceUUID
`DAF58E01`. The two devices share:

- the 128-bit custom UUID **stem `DAF58`** — differing only at the 6th nibble
  (`DAF58A01` vs `DAF58E01`, identical `…01` suffix), which reads as a
  device/model discriminator rather than a different vendor; and
- a **byte-for-byte identical manufacturer grammar**
  `<2-byte vanity CID> <4 identifier bytes> <00 00>`.

That shared fingerprint strongly suggests one vendor's product family. As with
the sibling, **no vendor is claimed** — the signals are surfaced (including a
`related_family` cross-reference) so future correlation can attach attribution.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer data CID | `0x6C14` (bytes `14 6c`, little-endian) |
| Manufacturer payload | `27 63 f0 7a 00 00` (4 identifier-looking bytes + 2 reserved zeros) |
| Service UUID (128-bit, custom) | `DAF58A01-…` (CoreBluetooth exported the 32-bit prefix in this capture) |
| Local name | absent |
| Service data | none |
| Address type | random |

### Captured sample

```
manufacturerDataHex:  146c2763f07a0000
serviceUUIDsJSON:     ["DAF58A01"]
sightingCount:        14   (single window; all folded to one adSignature)
rssiMax/Min:          -70 / -96 dBm
addressType:          random
```

The 14 sightings collapsed to a single `adSignature` → the manufacturer bytes
(including `27 63 f0 7a`) were byte-identical across the whole window; if the
4-byte identifier rotated, each value would have produced a distinct record.
This shows non-rotation over ~14 sightings in one window, not long-term
behaviour across MAC rotations.

### Stable Key

```
unknown_6c14_daf58a01:<mac>
```

MAC-scoped: single device, single window — we cannot yet tell whether the
4-byte mid-payload (`27 63 f0 7a`) is a stable device serial or a per-broadcast
nonce.

## What We Figured Out

- **CID `0x6C14` is not a SIG company identifier.** It is above the assigned
  ceiling — a vanity/unregistered value, the same category as the sibling's
  irregular use of `0xFE7C`.
- **Same family as the FE7C/DAF58E01 device.** Identical mfr grammar + shared
  `DAF58` UUID stem. Different vanity CID (`0x6C14` vs `0xFE7C`) and 6th UUID
  nibble, so the **UUID stem — not the CID — is the family anchor**.
- **Custom UUID does not match the SIG base.** `DAF58A01` is genuinely custom,
  not a SIG short-UUID expansion.

## What We Could NOT Figure Out

- **Vendor identity / product family.** No public references for `DAF58A01`,
  `DAF58`, `0x6C14`, or the payload prefix `27 63 f0 7a`.
- **Payload semantics.** The 4-byte identifier field could be a serial, a
  session nonce, a truncated MAC, or a tag — one window, so undecidable.

## Disjointness Rule (to Prevent Over-attribution)

- **Match only** when CID `0x6C14` appears in the manufacturer-data slot
  **and/or** a serviceUUID has the custom 32-bit prefix `daf58a01` followed by
  `-` or end-of-string.
- **Do NOT claim** the sibling's `0xFE7C` CID or its `DAF58E01` UUID — those
  belong to `unknown_fe7c_daf58e01`.
- `0x6C14` is not a SIG anything, so there is no legitimate service-UUID
  emission of it to mis-route.

## Detection Significance

- **Distinctive fingerprint pair.** Either signal alone is rare enough to avoid
  over-matching.
- **Surface-only catalog entry.** Emits beacon type `unknown_6c14_daf58a01`
  with `device_class: unknown` so the device appears in lists/counts and can be
  correlated against future sightings — and against its DAF58E01 sibling.

## References

- [Bluetooth SIG `company_identifiers.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x6C14` not present (above max ≈ `0x10E1`).
- [Bluetooth SIG `service_uuids.yaml` / `member_uuids.yaml`](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/) — no `DAF5*`.
- [`unknown-fe7c-daf58e01.md`](unknown-fe7c-daf58e01.md) — the sibling DAF58 device.
