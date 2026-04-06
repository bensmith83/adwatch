# Hunter Douglas PowerView Gen 3 — BLE Protocol Notes

## Overview

Hunter Douglas PowerView Gen 3 (launched 2022) motorized window shades use Bluetooth Low Energy for all shade communication, replacing the proprietary RF protocol of earlier generations. Each shade has a built-in BLE radio enabling direct smartphone control, real-time bidirectional communication (position reporting up to 8x/second), and integration with home automation systems.

The shades use AES-CTR encryption with a 16-byte "home key" for GATT commands, but the **advertisement data is unencrypted** and contains real-time shade state (position, tilt, battery level).

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `0xFDC1` | 16-bit, registered to Hunter Douglas by Bluetooth SIG |
| Company ID | `0x0819` (decimal 2073) | Hunter Douglas Inc |
| Local name | `XXX:YYYY` pattern | 3-letter product prefix + 4-char hex device ID |
| Address type | Random | BLE privacy enabled |

### Known Local Name Prefixes

| Prefix | Product Line | Type IDs | Description |
|--------|-------------|----------|-------------|
| `SIL:` | Silhouette | 18, 23 | Horizontal sheer shading with tiltable vanes |
| `DUE:` | Duette | 6, 8, 9, 10, 33 | Cellular/honeycomb shades |

Other prefixes likely exist for Vignette, Sonnette, Venetian, Parkland, Roman, etc. but have not been observed.

### Duette Type ID Variants

| Type ID | Variant |
|---------|---------|
| 6 | Duette (bottom up only) |
| 8 | Duette, Top Down Bottom Up |
| 9 | Duette DuoLite, Top Down Bottom Up |
| 10 | Duette and Applause SkyLift |
| 33 | Duette Architella, Top Down Bottom Up |

## Advertisement Structure

Each shade continuously broadcasts:

1. **Local Name**: `XXX:YYYY` format (shortened local name)
2. **Service UUID**: `0xFDC1` (Hunter Douglas shade service)
3. **Manufacturer Specific Data**: Company ID `0x0819` + 9 bytes payload

### Manufacturer Data Format (V2 Protocol)

The 9-byte payload (after the 2-byte company ID) encodes shade state:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0-1 | 2 | home_id | Little-endian uint16, identifies the PowerView home/network |
| 2 | 1 | type_id | Shade product type (see tables above) |
| 3-4 | 2 | position1 | LE uint16; bits [15:2] = primary position (÷10 for %); bits [1:0] = motion flags |
| 4-5 | -- | position2 | Overlapping nibble extraction: `(byte5 << 4) + (byte4 >> 4)`, then right-shift 2 |
| 6 | 1 | position3 | Third position axis (raw value) |
| 7 | 1 | tilt | Tilt/vane angle (0-255); only used by Silhouette and similar vane shades |
| 8 | 1 | status | Bits [7:6] = battery level; bit 1 = resetClock; bit 0 = resetMode |

#### Position1 Motion Flags (bits [1:0])

- `0x0`: Idle
- `0x1`: Closing
- `0x2`: Opening
- `0x3`: Battery charging

#### Battery Level (status byte bits [7:6])

- `0b11` (3): 100%
- `0b10` (2): 50%
- `0b01` (1): 20%
- `0b00` (0): 0%

#### Position Semantics by Product

| Product | position1 | position2 | position3 | tilt |
|---------|-----------|-----------|-----------|------|
| Silhouette | Primary (open/close) | Not used | Not used | Vane angle (0-255) |
| Duette (bottom up) | Bottom rail (0-100%) | Not used | Not used | Not used (always 0) |
| Duette TDBU | Bottom rail | Top rail | DuoLite fabric layer | Not used (always 0) |

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Product type | local_name prefix | SIL = Silhouette, DUE = Duette, etc. |
| Device ID | local_name suffix | 4-char hex identifier |
| Home network | home_id | Groups shades from same installation |
| Shade type | type_id | Specific product variant |
| Position | position1-3 | Real-time shade position (%) |
| Motion state | position1 bits [1:0] | Idle/opening/closing/charging |
| Tilt angle | tilt byte | Vane angle for Silhouette shades |
| Battery level | status bits [7:6] | 4 levels: 0/20/50/100% |

## GATT Services and Characteristics

When connected, the shade exposes:

| Service | UUID | Purpose |
|---------|------|---------|
| Shade Control | `0xFDC1` | Primary shade command service |
| Device Information | `0x180A` | Standard BLE device info |
| Battery | `0x180F` | Standard battery level service |

### Shade Control Characteristics

| Characteristic | UUID | Purpose |
|----------------|------|---------|
| TX (Command) | `CAFE1001-C0FF-EE01-8000-A110CA7AB1E0` | Send commands to shade |
| Unknown | `CAFE1002-C0FF-EE01-8000-A110CA7AB1E0` | Purpose TBD |

### Command Format

All commands: 2-byte command code (LE) + 1-byte sequence ID + 1-byte data length + payload. Encrypted with AES-CTR using the 16-byte home key.

| Command | Code | Payload |
|---------|------|---------|
| Set Position | `0x01F7` | pos1 (2B) + pos2 (2B) + pos3 (2B) + tilt (2B) + velocity (1B) |
| Stop | `0xB8F7` | None |
| Activate Scene | `0xBAF7` | scene_index + `0xA2` |
| Identify (Jog) | `0x11F7` | beep_count (1B, max 0xFF) |

## Known Protocol Details

- **Protocol Version**: V2 (9-byte manufacturer data format)
- **Encryption**: AES-CTR with 16-byte home key; required for GATT commands, not for reading advertisements
- **Home Key**: Shared across all shades in a PowerView home; can be extracted from the PowerView gateway or app configuration
- **Mesh Networking**: PowerView Gen 3 shades form a BLE mesh; the gateway (if present) bridges BLE to Wi-Fi for remote/cloud access

## Open Source References

- [patman15/hdpv_ble](https://github.com/patman15/hdpv_ble) — Home Assistant integration for PowerView BLE shades. Contains V2 manufacturer data parser, shade type database, command protocol, and encryption implementation.
- [openHAB bluetooth.hdpowerview binding](https://www.openhab.org/addons/bindings/bluetooth.hdpowerview/) — openHAB binding for PowerView Gen 3 shades via BLE.
- [openhab/openhab-addons (hdpowerview source)](https://github.com/openhab/openhab-addons/tree/main/bundles/org.openhab.binding.bluetooth.hdpowerview) — Source code for the openHAB binding.
- [sander76/aio-powerview-api](https://github.com/sander76/aio-powerview-api/issues/16) — Shade capabilities table mapping type IDs to products.
- [davidjbradshaw/homebridge-powerview-3](https://github.com/davidjbradshaw/homebridge-powerview-3) — Homebridge plugin with Duette TDBU support.
- [Bluetooth SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/) — Company ID `0x0819`, UUID `0xFDC1`.

## Observed in adwatch (April 2026 Export)

### Silhouette Shades

| Local Name | Sighting Count | RSSI Range | Home ID | Position | Battery |
|------------|---------------|------------|---------|----------|---------|
| `SIL:4914` | 185 | -86 to -104 dBm | 0x6C8A | Fully closed, tilt 0 | 100% |
| `SIL:E869` | 156 | -86 to -104 dBm | 0x6C8A | Fully closed, tilt 0 | 100% |

Both on the same home network, fully closed during the ~5 hour observation.

### Duette Shades

| Local Name | Sighting Count | RSSI Range | Home ID | Type | Position | Battery |
|------------|---------------|------------|---------|------|----------|---------|
| `DUE:1568` | 2 | -95 to -96 dBm | 0x6011 | DuoLite TDBU (9) | 72% open | 100% |

Different home network from the Silhouette shades. Brief appearance (only 2 sightings), likely at edge of BLE range.

### Raw Manufacturer Data Decodes

**SIL shades**: `19 08 8a 6c 17 00 00 00 00 00 c2` — home_id=0x6C8A, type=23 (Silhouette), position=0%, tilt=0, battery=100%

**DUE shade**: `19 08 11 60 09 40 0b 00 00 00 c2` — home_id=0x6011, type=9 (Duette DuoLite TDBU), position=72%, battery=100%
