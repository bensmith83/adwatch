# Wyze Sense Hub BLE Protocol

## Overview

**Wyze Labs, Inc.** ships several home-monitoring hubs under the **Wyze Sense Hub** family. The Sense Hub is the central coordinator for the Wyze Sense V2 ecosystem (contact sensors, motion sensors, leak sensors, climate sensors) and underpins the **Wyze Home Monitoring Service** (HMS) bundle. The closely related **Wyze Cam Floodlight Hub** also appears to share the same BLE advertising firmware family.

These hubs advertise via BLE using **Bluetooth SIG company identifier 0x0870 (Wyze Labs, Inc.)** with the GAP local-name `"wyze_hub"`. The 6-byte BLE MAC is embedded directly in the manufacturer payload, so a Sense Hub can be re-identified across MAC randomization windows by tracking the embedded MAC instead of the rotating peripheral identifier.

> Wyze has **two** separate SIG company-ID assignments. The Wyze Watch line uses **0x0649 (Ryeex Technology Co., Ltd.)** — Wyze's smartwatch ODM — and is handled by `WyzeWatchParser`. The Sense Hub uses Wyze's own SIG-assigned **0x0870**. This parser only claims the latter.

## Identifiers

- **Company ID:** `0x0870` (Wyze Labs, Inc.)
- **Local name:** `wyze_hub`
- **Device class:** `smart_home_hub`

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0870` | Wyze Labs, Inc. (SIG-assigned) |
| Local name | `wyze_hub` | Exact match (lowercase, underscore) |
| Address type | random | Hub rotates its peripheral identifier |

We match on **(CID == 0x0870)** AND **(local name == `"wyze_hub"` OR payload >= 9 bytes)**. Requiring CID 0x0870 keeps us strictly disjoint from `WyzeWatchParser` (which lives under 0x0649). The payload-length escape allows the parser to still classify if CoreBluetooth fails to surface the local-name field, which is common when the local name lives in the scan-response packet and the scan caches only the advertising packet.

### Manufacturer Data Structure

Total: 13 bytes observed (2-byte CID + 11-byte payload).

#### Example

```
70 08 04 02 dc 5a 33 2c 48 80 00 00 00
```

| Offset | Length | Value | Description |
|--------|--------|-------|-------------|
| 0-1 | 2 | `70 08` | Company ID 0x0870 little-endian (stripped from `manufacturerPayload`) |
| 2-3 | 2 | `04 02` | `device_type_hex` — device type / firmware variant |
| 4-9 | 6 | `dc 5a 33 2c 48 80` | Embedded BLE MAC, big-endian textual order |
| 10-12 | 3 | `00 00 00` | `tail_hex` — trailing reserved / state bytes |

In `manufacturerPayload` (post-CID) the offsets shift down by 2:

| Payload offset | Field | Notes |
|---|---|---|
| 0..1 | `device_type_hex` | Surfaced verbatim in metadata |
| 2..7 | `embedded_mac` | Formatted `xx:xx:xx:xx:xx:xx` |
| 8..end | `tail_hex` | Remaining bytes captured as hex |

### Embedded MAC

The 6 bytes at payload offset 2..7 (`dc 5a 33 2c 48 80` in the sample) are the hub's BLE MAC. In the sample capture, the OUI `dc:5a:33` belongs to **Hon Hai (Foxconn) Precision Industry** — a plausible ODM for a Wyze hardware build. The MAC is used as the stable key:

```
stable_key = "wyze_sense_hub:" + embedded_mac
identifier = SHA256(stable_key)[:16]
```

This means two adwatch sightings of the same physical hub will collapse to the same identifier hash even when CoreBluetooth's peripheral UUID rotates between sessions.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|---|---|---|
| Device presence | `company_id` 0x0870 | Wyze Sense Hub family nearby |
| Hub MAC | mfr payload bytes 2..7 | True BLE MAC, stable across sessions |
| Device type | mfr payload bytes 0..1 | Firmware/hardware variant; only `0402` seen so far |
| Trailing state | mfr payload bytes 8..end | Usually `000000`; semantics unknown |
| Local name | GAP local name | `wyze_hub` |

## What We Cannot Parse

- Paired-sensor inventory (requires GATT or Wyze cloud)
- HMS arm state (motion-armed / disarmed / panic)
- Firmware version (requires Device Information Service over GATT)
- Camera-hub specific fields (Cam Floodlight Hub may emit different `device_type` bytes)

## Examples

| Capture | Inference |
|---|---|
| CID `0x0870` + name `"wyze_hub"` + payload `0402dc5a332c4880000000` | Sense Hub, MAC `dc:5a:33:2c:48:80`, device type `0402` |
| CID `0x0870` + name `"wyze_hub"` + short 2-byte payload | Classified as Sense Hub but no MAC / stable key |
| CID `0x0870` only, no local name, full payload | Sense Hub fallback match via payload length |
| CID `0x0649` + name `"Wyze Watch 47"` | Handled by `WyzeWatchParser` — this parser ignores it |

## Detection Significance

- Indicates a Wyze ecosystem user with the **Home Monitoring Service** bundle or a Wyze hardware hub
- Often co-located with Wyze Cam, Wyze Bulbs, and Wyze Lock advertisements
- The hub itself is typically stationary (plugged into a wall outlet), so a persistent `wyze_sense_hub:` stable key is a strong location anchor

## References

- [Wyze Sense Hub product page](https://www.wyze.com/products/wyze-hms-bundle)
- [Wyze Labs corporate site](https://www.wyze.com)
- [Bluetooth SIG company identifier 0x0870 = "Wyze Labs, Inc"](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)
- Companion parser: `WyzeWatchParser` (CID 0x0649 / Ryeex Technology Co., Ltd. — Wyze Watch ODM)
