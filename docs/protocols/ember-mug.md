# Ember Mug (Heated Mug)

## Overview

Ember makes heated smart mugs and travel mugs that maintain a target drinking temperature. Devices broadcast model, generation, and color in BLE advertisements. Temperature and battery data require a GATT connection — this parser provides device identification and classification.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x03C1` (961) | Ember Technologies, Inc. |
| Local name | `Ember*` | Starts with "Ember" (default: "Ember Device") |
| Service UUID | See table below | Varies by product family |

### Service UUIDs

| UUID | Product Family |
|------|---------------|
| `fc543852-236c-4c94-8fa9-944a3e5353fa` | Mug / Cup / Tumbler |
| `fc543851-236c-4c94-8fa9-944a3e5353fa` | Travel Mug |
| `fc542191-236c-4c94-8fa9-944a3e5353fa` | Travel Mug (alt) |

All Ember UUIDs follow the template: `fc54{XXXX}-236c-4c94-8fa9-944a3e5353fa`

### Manufacturer Data Layout

**Extended format (≥ 4 bytes, preferred):**

| Offset | Field | Size | Decode | Unit |
|--------|-------|------|--------|------|
| 0 | Header | 1 byte | Unknown | — |
| 1 | Model ID | uint8 | See model table | — |
| 2 | Generation | uint8 | 0-1 = Gen 1, ≥2 = Gen 2 | — |
| 3 | Color ID | uint8 | See color table | — |

**Short format (< 4 bytes):**
- Entire payload is a big-endian signed integer used as `model_id`

### Model ID Lookup

| model_id | Gen 1 (gen < 2) | Gen 2 (gen ≥ 2) |
|----------|-----------------|-----------------|
| 1 | Mug (10oz) | Mug 2 (10oz) |
| 2, 120 | Mug (14oz) | Mug 2 (14oz) |
| 3 | Travel Mug | Travel Mug |
| 8 | Cup (6oz) | Cup (6oz) |
| 9 | Tumbler (16oz) | Tumbler (16oz) |

### Color ID Lookup (selected)

| Color ID(s) | Color |
|-------------|-------|
| -127, -63, 1, 14, 65 | Black |
| -126, -62, 2 | White |
| -120, -117, -56, -53, 8, 11 | Red |
| -131, -125, -61, 3, 51, 83 | Copper |
| -124, -60 | Rose Gold |
| -123, -59 | Stainless Steel |
| -51 | Sandstone |
| -52 | Sage Green |
| -55 | Grey |
| -57 | Blue |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Product model | mfr_data[1] | Mug, Cup, Tumbler, Travel Mug |
| Generation | mfr_data[2] | Gen 1 vs Gen 2 |
| Color | mfr_data[3] | Physical device color |
| Product family | Service UUID | Mug/Cup vs Travel Mug |

### What Requires GATT Connection

- Current temperature (°C)
- Target temperature (°C)
- Battery percent + charging state
- Liquid level (0-30 scale)
- Liquid state (standby, empty, filling, cold, cooling, heating, at target, warm)
- LED color, firmware, serial number

## Identity Hashing

```
identifier = SHA256("{mac}:Ember")[:16]
```

## Detection Significance

- Popular consumer product, recognizable brand
- Model + color identification is fun metadata
- Indicates someone is likely at a desk/workspace
- Gen 1 vs Gen 2 distinction is useful

## References

- [orlopau/ember-mug](https://github.com/orlopau/ember-mug) — Reverse-engineered protocol
- [sopelj/python-ember-mug](https://github.com/sopelj/python-ember-mug) — Python library (byte-level details)
