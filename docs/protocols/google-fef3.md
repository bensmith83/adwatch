# Google FEF3 Service (Google Nearby / Cross-Device Companion)

## Overview

`0xFEF3` is a Bluetooth-SIG-assigned 16-bit service UUID belonging to **Google LLC** (member UUIDs registry). The FEF3 frame is broadcast by Google Play services on a subset of Android phones, Chromecast-with-Google-TV, Pixel Tab, and Nest Hub devices to support an undocumented sibling of the Cross-Device framework. Like the related `0xFCF1` and `0xFE9F`, it carries an opaque rotating identifier and is only fully resolvable to devices that share an account-derived key.

The frame layout is similar to (but distinct from) FCF1: a 1-byte type prefix followed by a 26-byte rotating payload.

## Identifiers

- **Service UUID:** `0xFEF3` (full: `0000fef3-0000-1000-8000-00805f9b34fb`)
- **Manufacturer:** Google LLC (BT SIG member-UUID assignment)
- **Device class:** `phone` / `media_device`
- **Local name:** typically empty

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `FEF3` | Always present |
| Service Data | 27-byte rotating frame | Required for parse |
| Local name | empty | Privacy default |
| Manufacturer Data | none | — |

### Service Data Layout (27 bytes)

```
4a 17 23 4e 38 48 4e 11 32 85 6c 7d b5 ee 69 43 c6 4d 4b ba 81 d8 4e fe d4 ac 8f
└─ ─────────────────────────── rotating opaque identifier ─────────────────────────┘
```

| Offset | Length | Description |
|--------|--------|-------------|
| 0-26 | 27 | Rotating opaque payload — no field-level structure visible |

Two distinct samples observed share no bytes in common at any offset, indicating the frame is fully randomized per rotation rather than carrying a typed header.

### Two-Frame Sample

```
Sample 1: 4a17234e38484e1132856c7db5ee6943c64d4bba81d84efed4ac8f
Sample 2: 4a17234e38484e1132856c7db5ee6943c64d4bba81d84efed432d3
```

Note: Sample 1 and Sample 2 differ only in the trailing 2 bytes — likely a CRC, sequence counter, or short rotation period.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | service_uuid | Google |
| Payload length | service_data length | 27 bytes observed |
| Rotation | observe over time | Trailing bytes change rapidly |

### What We Cannot Parse

- Source device identity
- Account / user
- Stable hardware ID
- Feature in use

## Sample Advertisements

```
Device:
  Service UUIDs: []
  Service Data:  {"FEF3": "4a17234e38484e1132856c7db5ee6943c64d4bba81d84efed4ac8f"}
  Sightings:     3
```

## Identity Hashing

```
identifier = SHA256("google_fef3:{mac}")[:16]
```

Same caveat as FCF1: rotating RPA defeats stable identification.

## Detection Significance

- Indicates a Google-ecosystem device using a less common Cross-Device beacon path
- Often co-observed alongside Chromecast/Google-TV-class devices and Nest Hubs
- Lower volume than FCF1 / FE9F — opportunistic rather than continuous beacon

## Parsing Strategy

1. Match on `FEF3` in `service_data`
2. Capture `payload_hex` and `payload_length`
3. Return device class `phone` (best-effort), beacon type `google_fef3`

## References

- BT SIG member UUIDs: `0xFEF3` = Google LLC
- [Google Nearby Connections overview](https://developers.google.com/nearby/connections/overview)
- Adjacent surfaces: [`google-fcf1.md`](./google-fcf1.md), [`google-fast-pair-fe2c.md`](./google-fast-pair-fe2c.md)
