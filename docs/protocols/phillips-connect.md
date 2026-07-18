# Phillips Connect smart-trailer telematics

## Overview

[Phillips Connect Technologies](https://phillips-connect.com/) instruments
commercial semi-trailers with telematics gateways (Smart7 / StealthNet /
SolarNet families) and BLE-linked wireless cameras (CargoVision /
BackupVision). The cameras deliver imagery over Bluetooth to the trailer's
gateway, which backhauls over cellular. Passively, an instrumented trailer
driving past looks like a small cluster of BLE devices — one gateway plus one
or more cameras — appearing together for a few seconds.

Company ID `0x087F` is SIG-registered to **Phillips Connect Technologies
LLC**, and the devices name themselves with the vendor's product acronyms, so
attribution is high-confidence.

> **Privacy note.** The gateway broadcasts its full **cellular IMEI in
> cleartext** inside the BLE advertisement. An IMEI is a stable global
> identifier; broadcasting it defeats the point of the device's random BLE
> address and makes the trailer trivially re-identifiable across sightings.

## Supported roles

| Local name | Role | Frame |
|------------|------|-------|
| `PCTGW_<n>` | Trailer telematics gateway | 13-byte, IMEI in BCD |
| `V<digits>` | Gateway (fleet asset-number named) | 13-byte, IMEI in BCD |
| `PCAM_<hex>` | Wireless trailer camera | 8-byte |

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x087F` | SIG-registered to Phillips Connect Technologies LLC |
| Frame selector | mfr bytes 2-3 | `00 00` = gateway, `0A 01` = camera |
| Local name | `PCTGW_*` / `PCAM_*` / `V######` | Optional but corroborating |
| Address type | random | Drive-by, weak-to-moderate RSSI |

### Gateway frame (13 bytes)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 2 | Company ID | `7F 08` (LE → 0x087F) |
| 2 | 2 | Frame selector | `00 00` |
| 4 | 9 | IMEI (BCD) | 18 nibbles = `000` zero-pad + 15-digit IMEI |

The 15-digit IMEI is Luhn-valid. Both captured units share TAC `86696106`
(same cellular module model). For `PCTGW_<n>` the name suffix equals the last
five IMEI digits — a self-confirming decode. `V######` gateways name
themselves with a fleet asset number instead.

### Camera frame (8 bytes)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0 | 2 | Company ID | `7F 08` |
| 2 | 2 | Frame selector | `0A 01` |
| 4 | 1 | Constant | `0x1A` in all captures |
| 5 | 1 | Frame counter | ticks between adverts (`0x1B`→`0x1C` in ~2 s) |
| 6 | 2 | Per-unit tag | stable per camera (`6E47`, `787C`) |

### Captured frames

| local name | mfr data |
|------------|----------|
| `PCTGW_24783` | `7f 08 00 00 00 08 66 96 10 62 22 47 83` → IMEI 866961062224783 |
| `V571536` | `7f 08 00 00 00 08 66 96 10 69 83 92 29` → IMEI 866961069839229 |
| `PCAM_E719EB` | `7f 08 0a 01 1a 1c 6e 47` |
| `PCAM_E719EB` | `7f 08 0a 01 1a 1b 6e 47` |
| `PCAM_8985EF` | `7f 08 0a 01 1a 1c 78 7c` |

## What We Can Parse

- Vendor presence (Phillips Connect) and device role (gateway vs camera)
- Gateway **IMEI** (cleartext) and its TAC → cellular module family
- Stable identity: IMEI for gateways, per-unit tag for cameras (both survive
  BLE address rotation)

## What We Cannot Parse

- Cargo / door / tire-pressure telemetry (cellular- or GATT-side)
- Camera imagery (BLE link to the gateway, not advertised)
- Which specific gateway/camera SKU within the product line

## Parser scope

Passive presence + identity only. `PhillipsConnectParser` routes on company
ID `0x087F`, decodes the two known frame types, and attributes unknown
subtypes to the vendor with `role="unknown"`.

## Confidence / attribution

**High.** SIG-registered company ID + vendor-acronym local names + a
self-confirming IMEI/name-suffix match on the gateway. Frame internals
(counter, per-unit tag) are validated across all corpus records but their
finer semantics (what the camera counter counts) are unconfirmed.

## References

- Bluetooth SIG company identifiers: `0x087F` = Phillips Connect Technologies LLC
- phillips-connect.com — trailer gateways and CargoVision wireless camera (BLE camera↔gateway link)
- First seen: NearSight fresh-eyes telemetry sweep, 2026-07-01 (2 drive-by encounters, 5 records)
