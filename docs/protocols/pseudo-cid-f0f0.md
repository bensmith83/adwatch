# Pseudo Company-ID 0xF0F0 (Self-Assigned CID Cluster)

## Overview

`0xF0F0` is **not** a Bluetooth SIG-assigned company identifier. The
SIG `company_identifiers.yaml` registry has no entry there, and the
alternating-nibble shape `F0F0` is the canonical "obviously fake" hex
that DIY firmware authors and white-label SDK integrators pick when
they don't want to (or can't) pay for an official allocation.

This is a **family fingerprint, not a vendor parser** — we cluster the
seven distinct devices observed in our nearsight export under one
forensic cluster on the strength of the CID + payload shape, while
deliberately leaving `vendor=Unknown`. Upgrade to a real vendor parser
when ground truth surfaces (sniffed pairing flow, app reverse, matching
IEEE OUI on a public-address sighting).

## Observed Cluster

Seven distinct devices in `research/nearsight_export 2.json`,
~17 sightings combined:

| Payload (hex) | localName | Sightings | Devices |
|---|---|---|---|
| `098bc5fb071cdecbead630213fb67754` | `"2"` | 14 | 2 |
| `4fd3b04b897ff11d34d3b862daafa599` | `"7"` | 4 | 2 |
| `ae89b04f1506c0ea3929cf548f002008` | (none) | 3 | 1 |
| `44acce91211a49f617f88818418833fa` | (none) | 2 | 1 |
| `5519da302da7571faa3a97442c024096` | (none) | 3 | 2 |
| `f48990e111bca445a0925c4fd7828873` | (none) | 1 | 1 |

All payloads are exactly **16 bytes** after the 2-byte `f0 f0` CID
prefix. 16 bytes is exactly the AES-128 block size — strong heuristic
evidence that the payload is an encrypted / rolling identifier rather
than plaintext telemetry. The high byte entropy across all six payload
fingerprints supports the ciphertext hypothesis.

The single-digit local names `"2"` and `"7"` strongly suggest a
**multi-pack** of N sensors / buttons / contact-tags where each unit
gets an index in `1..N`. The other five units in the cluster either
suppress the name or rotate it.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x00F0` (LE bytes `f0 f0`) → parsed as `0xF0F0` | **Not in BT SIG `company_identifiers.yaml`**; self-assigned pseudo-CID |
| Manufacturer payload | 16 bytes (in observed captures) | High-entropy; matches AES-128 block size |
| Local name | Optional; single decimal digit (`"2"`, `"7"`) when present | Pack-index hint |
| Service UUIDs | (none) | — |
| Service data | (none) | — |
| Address type | `random` | Rotating private address |

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Unknown` |
| Attribution | hard-coded | `unknown_self_assigned_cid` |
| Device class | hard-coded | `unknown_beacon` |
| Family signature | hard-coded | `pseudo_cid_f0f0` |
| `pseudo_company_id` | hard-coded | `0xF0F0` |
| `payload_hex` | mfg payload | exact bytes after the CID |
| `payload_length` | mfg payload byte count | typically `16` |
| `payload_size_note` | derived | `matches_aes128_block_size` when payload is exactly 16 bytes |
| `pack_index` | localName | only when localName is purely digits |
| `local_name` | localName | when present |

### What We Cannot Parse from the Advertisement

- The vendor or product line — `0xF0F0` is unattributed, and no public
  fingerprint database matches the 16-byte payload signature.
- The payload semantics — almost certainly an encrypted rolling token
  that needs the per-device key (held by the companion app the device
  was paired with).
- Battery, sensor state, button events — all opaque inside the
  ciphertext.
- The number of devices in the pack — we see units `"2"` and `"7"` in
  this capture, so the pack is at least size 7, but the upper bound is
  unknown.

## Stable Identity

Two physically distinct units in the export share the **same payload
value** under rotating MACs — confirming the payload bytes are the
better stable anchor than the OS-rotated `ad.macAddress`. We key on
the payload:

```
stable_key = pseudo_cid_f0f0:payload:<32-hex>
```

If the payload were a per-advertisement rolling token (vs a per-device
constant), this key would mis-cluster — but the current observation
window shows the same payload re-appearing across multiple sightings,
consistent with a per-device constant or a slow-rotating identifier.
Revisit if longer captures show the payload churning per advertisement.

## Detection Significance

- A cluster of `pseudo_cid_f0f0` devices at one site is a signature
  of either:
  1. An installed multi-pack accessory (8-pack of contact sensors, a
     wireless-button quiz remote, motion sensors, asset tags), or
  2. A DIY / hobbyist firmware build that picked the placeholder CID.
- The presence of pack-index names (`"2"`, `"7"`) tilts strongly toward
  interpretation (1) — manufacturers ship multi-packs with sequential
  numbering; DIYers usually don't.
- 16-byte high-entropy payloads are common in low-end Chinese ODM
  asset trackers and door/window contact sensor families
  (Tuya-adjacent, Mijia-adjacent — but neither match this exact CID
  signature).

## Upgrade Path

The 16-byte payload shape is consistent with these candidate vendors;
we have not yet found a match for any:

| Candidate | Why considered | Why ruled out (so far) |
|-----------|----------------|-------------------------|
| Tuya | Common pseudo-CID squatter | Tuya uses service UUID `0xFD50`, not CID 0xF0F0 |
| Mijia (Xiaomi BLE) | Encrypted rolling token + 16-byte payload | Mijia uses CID `0x038F` + service data on `0xFE95` |
| Govee | Multi-pack consumer pattern | Govee CID is `0xEC88` |
| ThermoPro | Multi-sensor packs | ThermoPro uses CID `0x0067` with deterministic temp/humidity in plaintext |
| BloomBaby (`0xB10D`) | Sibling unknown cluster in same export | Different signal shape (service-UUID-based, not CID-based) |

A pairing-app sniff or a matching IEEE OUI lookup on a public-address
sighting would unblock vendor attribution.

## References

- [BT SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms 0xF0F0 unassigned
- [reelyActive BLE identifier reference](https://reelyactive.github.io/ble-identifier-reference.html) — catalog of common self-assigned / placeholder CIDs
- [Nordic Semiconductor bluetooth-numbers-database](https://github.com/NordicSemiconductor/bluetooth-numbers-database) — corroborating CID source
- Nearsight export: `research/nearsight_export 2.json`, 7 devices, ~17 sightings (2026-06-04 to 2026-06-05)
