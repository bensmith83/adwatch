# Leica Camera AG Plugin

## Overview

**Leica Camera AG** (Wetzlar, Germany) is a premium German mirrorless / fixed-lens camera maker. Modern Leica cameras — the **SL** (full-frame interchangeable-lens), **Q** (full-frame fixed-lens), and **M** (rangefinder) lines — pair with the **Leica FOTOS** mobile companion app over BLE for:

- **GPS geotagging** — the paired phone forwards its position fix to the camera so JPEGs are stamped with location at capture time.
- **Remote shutter / live-view preview** — the phone acts as a wireless trigger and viewfinder.
- **Image transfer handshake** — BLE negotiates the session; Wi-Fi takes over for bulk JPEG / DNG transfer.

Identified models in our captures: `Leica SL3`, `Leica Q3`, `Leica Q3 43`.

Note: Leica's surveying / geomatics arm, **Leica Geosystems AG**, holds a *different* SIG company identifier (`0x0D09`). It manufactures the **Leica DISTO** laser-distance meters and total stations and is out of scope for this plugin.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Manufacturer-data CID | `0x1A05` (decoded little-endian; raw bytes `05 1a`) |
| SIG-assigned ID for Leica Camera AG | `0x051A` |
| Service UUID (128-bit) | `E273BF5F-7065-4C43-BBF1-818CDFDDB5C4` (Leica FOTOS pairing service) |
| Local name | `"Leica <model>"` — e.g. `"Leica SL3"`, `"Leica Q3"`, `"Leica Q3 43"` |

The byte ordering deserves a note. The Bluetooth SIG assigns Leica Camera AG the identifier `0x051A`. Cameras transmit the two-byte CID as `05 1a` on the wire, which is the **big-endian** byte order — most SIG implementations transmit little-endian, so `CBPeripheral`'s `companyID` decode reads it as `0x1A05`. We match against the decoded `0x1A05` form (what `RawAdvertisement.companyID` returns). Either interpretation is unique on the air.

Any one of the three signals is sufficient to identify the device. The local-name match requires the trailing space (`"Leica "`) so we don't false-positive on unrelated products that contain the substring `Leica` without that delimiter.

### Manufacturer-Data Payload Layout

The total manufacturer-data block is 8 bytes — a 2-byte CID plus a 6-byte payload:

```
05 1a | FT | ?? ?? ?? | CC CC
──┬── ─┬── ──────┬──── ──┬──
 CID  frame   model?   counter-like
       type   (3 bytes)
```

| Byte | Meaning | Notes |
|---|---|---|
| 0 | Frame type | `06` or `07` observed. Precise meaning undocumented — likely a pairing-state / advertising-mode flag. |
| 1-3 | Model family (tentative) | Correlates with hardware: `26 ef ed` on SL3, `65 3a ..` on Q3 family. |
| 4-5 | Counter-like | Varies frame-to-frame; not decoded. |

### Observed Payloads

| Local name | Raw mfr data | Payload (bytes after CID) | Frame byte |
|---|---|---|---|
| `Leica SL3` | `051a0726efedf87d` | `07 26 ef ed f8 7d` | `07` |
| `Leica SL3` | `051a0726efedff65` | `07 26 ef ed ff 65` | `07` |
| `Leica Q3 43` | `051a06653a2e8dbe` | `06 65 3a 2e 8d be` | `06` |
| `Leica Q3` | `051a07653ac71702` | `07 65 3a c7 17 02` | `07` |

We surface the entire 6-byte payload as `payload_hex` and the frame byte as `frame_byte_hex` for future analysis but do not key on either; the stable key is the marketing model name when present.

## Examples

| Capture | Inference |
|---|---|
| CID `0x1A05` + FOTOS UUID + name `"Leica SL3"` | model = `Leica SL3`, class = `camera`, stable key `leica:Leica SL3` |
| CID `0x1A05` + name `"Leica Q3 43"` | model = `Leica Q3 43`, class = `camera` |
| FOTOS UUID only, no name | matched on UUID; class = `camera`, no stable key |
| CID `0x1A05` only | matched on company ID; class = `camera` |

## References

- [Leica FOTOS app overview (Leica Camera US)](https://leica-camera.com/en-US/photography/leica-apps/leica-fotos)
- [Leica FOTOS — Apple App Store](https://apps.apple.com/us/app/leica-fotos/id1356061526)
- [Leica Q3 user manual, "Connecting With Paired Devices"](https://www.manualslib.com/manual/3104954/Leica-Q3.html?page=233)
- Bluetooth SIG `company_identifiers.yaml`: `0x051A` = Leica Camera AG (and `0x0D09` = Leica Geosystems AG, distinct)
