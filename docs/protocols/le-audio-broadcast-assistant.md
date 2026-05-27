# LE Audio Broadcast Assistant (Auracast) BLE Protocol

## Overview

LE Audio is the next-generation Bluetooth audio stack standardised by the Bluetooth SIG (Core 5.3+, BAP 1.0, BASS 1.0). A central role in the architecture is the **Broadcast Assistant** — a phone, watch, or hearable that *scans* on behalf of a remote sink (typically a hearing aid or LE Audio earbud) to discover Auracast broadcast sources nearby.

When a host is acting as a Broadcast Assistant, its advertisement includes three SIG-standard 16-bit service UUIDs that travel together:

- **`0x184E`** — Audio Stream Control Service (ASCS)
- **`0x184F`** — Broadcast Audio Scan Service (BASS)
- **`0x1853`** — Common Audio Service (CAS)

These are *not* member UUIDs — they're public service UUIDs in the SIG standard set, used by every conformant LE Audio implementation.

## Identifiers

- **Service UUIDs:** `184E`, `184F`, `1853` (any one is enough to route the frame; all three together is the canonical Broadcast Assistant signature)
- **Vendor-agnostic:** any LE Audio device — iOS 18 phones, Pixel 8+, Galaxy S24+, Samsung TVs, LE Audio hearables, smart-glasses
- **Device class:** `audio_le_audio`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUIDs | `184E` + `184F` + `1853` | Canonical triple; ASCS alone is enough to detect |
| Service data `184E` | 6-byte "available context" bitmap | Per CAS spec |
| Service data `184F` | empty | Marker only — BASS state lives over GATT |
| Service data `1853` | 1-byte scan-state | CAS scan-state indicator |

### Service-data byte map (`184E`)

The CAS "Available Audio Contexts" characteristic is a 16-bit little-endian bitmap padded to 6 bytes when broadcast:

| Bit | Hex | Context name |
|-----|-----|--------------|
| 0 | `0x0001` | unspecified |
| 1 | `0x0002` | conversational |
| 2 | `0x0004` | media |
| 3 | `0x0008` | game |
| 4 | `0x0010` | instructional |
| 5 | `0x0020` | voice_assistants |
| 6 | `0x0040` | live |
| 7 | `0x0080` | sound_effects |
| 8 | `0x0100` | notifications |
| 9 | `0x0200` | ringtone |
| 10 | `0x0400` | alerts |
| 11 | `0x0800` | emergency_alarm |

### Service-data byte map (`1853`)

The Common Audio Service emits a single state byte:

| Value | Meaning |
|-------|---------|
| `0x00` | idle |
| `0x01` | scanning (looking for Auracast sources) |
| `0x02` | source_discovered |
| `0x03` | synchronized |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | any of `184E`/`184F`/`1853` | LE Audio host nearby |
| Available contexts | service_data[184E] | Decoded into named contexts |
| Scan state | service_data[1853] | idle / scanning / discovered / synchronized |
| BASS support | service_uuid[184F] | Whether the host can manage broadcast sources |

### What We Cannot Parse (requires GATT)

- Specific broadcast source identifiers (the BAA "Broadcast Audio Announcement" carries the BIG ID — different parser)
- Connection to a specific stream
- Codec / quality parameters
- Sink-side context (which hearable the assistant is helping)
- Encryption keys for encrypted Auracast streams

## Sample Advertisements

```
LE Audio Broadcast Assistant — 2 sightings (one of multiple units in scan)
  Service UUIDs: ["184E", "184F", "1853"]
  Service data:
    "184E": "010000000000"   # bit 0 = "unspecified" context advertised
    "184F": ""                # marker only
    "1853": "01"              # scanning
  Manufacturer data: (none)
  Address: random (rotates)
```

## Identity Hashing

```
identifier = SHA256("le_audio:{mac}")[:16]
```

Broadcast Assistants advertise with a rotating random address; there is no stable identity in the public advertisement. The identifier is therefore presence-only and survives only as long as the address remains the same.

## Detection Significance

- LE Audio rollout is in mainstream device fleets as of iOS 18, Pixel 8+, Galaxy S24, and Samsung TV firmware 2024+
- Volume of these frames will grow as Auracast adoption expands
- Provides early signal that an LE-Audio capable phone, TV, or hearable is nearby — useful for accessibility and audio-environment context

## Parsing Strategy

1. Require at least one of `184E`, `184F`, or `1853` to match (`184E` ASCS is the strongest signal; some sink-only hosts emit only ASCS)
2. If `serviceData[184E]` is present, decode the 16-bit little-endian context bitmap into a comma-separated list of context names
3. If `serviceData[1853]` is present, map the first byte to `idle`/`scanning`/`source_discovered`/`synchronized`
4. Report `cas_present` / `bass_present` booleans so downstream callers can distinguish Broadcast Assistant from broadcast-source-only emitters
5. Return device class `audio_le_audio` with `vendor="Bluetooth SIG (LE Audio)"`

## References

- [Bluetooth SIG — LE Audio specifications](https://www.bluetooth.com/specifications/specs/) — BAP 1.0, BASS 1.0, ASCS 1.0, CAS 1.0
- [Bluetooth SIG Assigned Numbers — service UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/service_uuids.yaml) — `0x184E Audio Stream Control`, `0x184F Broadcast Audio Scan`, `0x1853 Common Audio`
- [Auracast™ broadcast audio](https://www.bluetooth.com/auracast/) — vendor-facing overview
- Observed in `research/adwatch_export 12.json` — multiple distinct rotating-address units across the capture window
