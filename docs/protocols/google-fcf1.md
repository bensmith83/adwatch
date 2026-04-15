# Google FCF1 Service (Cross-Device Account-Key Beacon)

## Overview

`0xFCF1` is a Bluetooth-SIG-assigned 16-bit service UUID belonging to **Google LLC** (member UUIDs registry). It is used by recent versions of Google Play services (Pixel + Android 14/15) for an undocumented "Cross-Device" framework — the same machinery that powers Phone Hub, Quick Share device discovery, and the new account-key-based proximity surface that complements Fast Pair (`0xFE2C`) and Nearby Presence (`0xFE2C` / `0xFE9F`).

Unlike Fast Pair, the FCF1 frame does not contain a model ID. It rotates every few minutes and is intentionally opaque to non-account observers.

## Identifiers

- **Service UUID:** `0xFCF1` (full: `0000fcf1-0000-1000-8000-00805f9b34fb`)
- **Manufacturer:** Google LLC (BT SIG member-UUID assignment)
- **Device class:** `phone` / `wearable` / `tablet`
- **Local name:** typically empty (privacy)

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FCF1` | Always present |
| Service Data | 22-byte rotating frame | Required for parse |
| Local name | empty | Privacy default |
| Manufacturer Data | none | — |

### Service Data Layout (22 bytes)

```
04 5d f4 8a e9 ed 11 56 04 78 e7 3f 8c 3f e9 cb 28 34 30 26 a4 7a
│  └─────────────── rotating ephemeral identifier (21 bytes) ─────┘
└─ Frame type / version (0x04 observed)
```

| Offset | Length | Description |
|--------|--------|-------------|
| 0 | 1 | Frame type (`0x04` is the only value observed) |
| 1-21 | 21 | Encrypted/rotating ephemeral identifier — opaque to non-account observers |

### Two-Frame Sample

```
Sample 1: 04 5d f4 8a e9 ed 11 56 04 78 e7 3f 8c 3f e9 cb 28 34 30 26 a4 7a
Sample 2: 04 27 49 6f 33 35 4e bb 22 1c 0a 87 ad 1e f1 dc c6 95 4a e7 89
Sample 3: 04 7e 9c c0 7b 97 2f 27 26 d2 e3 cd e6 1f 54 08 91 6b 0b e9 bf
```

The first byte is constant (`0x04`), indicating frame type. The remaining 21 bytes change on every rotation interval — there is no field-level structure visible from a passive observer.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | service_uuid | Google |
| Frame type | service_data[0] | `0x04` so far |
| Rotation | observe over time | New value ≈ every 15 min |

### What We Cannot Parse (requires account / decryption keys)

- Source device identity (Pixel, Pixel Watch, Galaxy Tab, etc.)
- User account
- Stable hardware ID
- Specific Cross-Device feature in use (Phone Hub vs. Quick Share vs. Nearby Presence)

## Sample Advertisements

```
Device A:
  Service UUIDs: ["FCF1"]
  Service Data:  {"FCF1": "045df48ae9ed11560478e73f8c3fe9cb28343026a47a"}
  Sightings:     19

Device B:
  Service UUIDs: ["FCF1"]
  Service Data:  {"FCF1": "0427496f33354ebb221c0a87ad1ef1dcc6954ae789"}
  Sightings:     10
```

## Identity Hashing

Because the frame rotates intentionally to defeat tracking, the only stable handle we have is the BLE MAC — which is itself a resolvable private address. Best-effort:

```
identifier = SHA256("google_fcf1:{mac}")[:16]
```

The same logical device will be observed under multiple identifier hashes as the OS rotates its RPA.

## Detection Significance

- Indicates a Google ecosystem device (Pixel, Pixel Tab, Pixel Watch, ChromeOS) within range
- Co-occurrence with `FE2C` (Fast Pair / FMDN) or `FE9F` (Google Nearby Presence) increases confidence it is a Pixel-class phone
- Useful for presence-detection but cannot be used to track a specific user across rotation events without the account key

## Parsing Strategy

1. Match on `FCF1` in `service_data`
2. Validate first byte == `0x04` (currently the only known frame type)
3. Capture `payload_hex` and `payload_length` for the explorer / spec UI
4. Return device class `phone` (best-effort), beacon type `google_fcf1`

## References

- BT SIG member UUIDs: `0xFCF1` = Google LLC
- [Google Issue Tracker #398554946](https://issuetracker.google.com/issues/398554946) — public report of `0xFCF1` ATT service on Pixel devices
- [Google Cross-Device Services overview](https://developers.google.com/nearby) — adjacent feature surface
