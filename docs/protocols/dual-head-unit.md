# Dual Electronics Car / Marine Head Unit (Dual iPlug)

## Overview

**Dual Electronics** (Namsung America) makes 12 V in-dash car and marine
audio head units sold through Walmart, Amazon, Best Buy, and the marine
aftermarket. Their multi-product line — **XDM**, **XRM**, **XVM**, and
**XDMBT** families (e.g. XDM17BT, XDM27BT, XDM290BT, XRM59BT, XRM69BT,
XVM279BT, XDM9Q) — uses a common Bluetooth firmware that pairs with the
**Dual iPlug** iOS/Android companion app for source switching, EQ, and
basic preset management.

When the head unit is powered and not yet paired, it broadcasts an
identifying advertisement so the companion app can discover it. Unlike
typical BLE devices, the head unit does **not** encode a SIG-assigned
company ID; instead it dumps the literal ASCII string `"Dual iPlug"`
into manufacturer-specific-data starting at offset 0.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | (empty) | Head unit publishes no advertisement local name |
| Manufacturer data | `44 75 61 6c 20 69 50 6c 75 67` | Literal ASCII `"Dual iPlug"` — **10 bytes, no real CID** |
| Service UUIDs | (absent) | All services live behind GATT, post-pair |
| Service data | (absent) | — |
| Address type | `random` | Rotating private address |
| Typical RSSI | -95 to -75 | Vehicle metal enclosure attenuates considerably |

**Unusual encoding note.** The first two manufacturer-data bytes
(`0x44 0x75`, little-endian decode → CID `0x7544`) are *not* an
allocation in the BT SIG `member_uuids.yaml` registry — they are simply
ASCII `"uD"`, the first two characters of `"Dual iPlug"`. The firmware
skips the SIG company-ID convention entirely and treats the
manufacturer-data field as a raw branding string buffer. Any parser
that gates on `companyID` will mis-classify this device; the only
reliable identification is a **literal ASCII subsequence match** for
the 10-byte signature anywhere inside the manufacturer-data payload.

### Signature

```
hex:   44 75 61 6c 20 69 50 6c 75 67
ascii:  D  u  a  l     i  P  l  u  g
```

Some firmware revisions may pad or prefix the buffer with additional
bytes; the parser therefore matches on subsequence containment rather
than equality or a leading-bytes test.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Dual Electronics` |
| Product family | hard-coded | `XDM/XRM/XVM head units` |
| Device class | hard-coded | `head_unit` |
| Identification method | hard-coded | `mfg_ascii_signature` |
| Signature hex | hard-coded | `4475616c2069506c7567` |
| Payload hex | mfg data | Full raw manufacturer-data bytes |

### What We Cannot Parse from the Advertisement

- **Specific head-unit model** (XDM17BT vs XDM290BT vs XVM279BT etc.) —
  every product in the family shares the same `"Dual iPlug"` string.
- **Firmware version** — not exposed in the advertisement.
- **Active source** (AM/FM, USB, AUX, Bluetooth audio, SiriusXM) —
  GATT-only after pair.
- **Volume / EQ preset / current track metadata** — GATT-only.
- **Whether the host vehicle is a car, RV, or marine vessel** — the
  same firmware ships across automotive and marine SKUs.

All post-identification telemetry lives behind a vendor GATT service
that has not been publicly documented; the parser deliberately stops
at presence + family.

## Stable Identity

There is no per-unit identifier in the advertisement — the signature
string is identical across every XDM/XRM/XVM unit ever sold. The
rotating random MAC is the only available discriminator, so:

```
stable_key = dual_head_unit:mac:<mac>
```

This means a head unit will appear as a "new" device after each MAC
rotation. That's an acceptable trade-off because the detection
significance (a *vehicle nearby*) is more useful than per-unit
tracking would be.

## Detection Significance

- Strong **vehicle context** clue: car, RV, motorhome, boat, or
  powersports cabin. Dual head units are not installed in homes,
  offices, or fixed venues.
- The marine SKUs (XRM, XVM, XMR series) imply a boat slip, dock,
  marina, lakefront, or coastal parking lot.
- A persistent Dual signature in a parking-lot capture suggests the
  vehicle is occupied or recently switched on — these head units
  advertise only while ignition / accessory power is live.
- Co-detection with other automotive BLE shapes (TPMS, OBD-II
  dongles, dashcams, car-key fobs) reinforces a vehicle-cabin
  fingerprint.

## References

- iOS app: <https://apps.apple.com/us/app/dual-iplug/id1216140105>
- Android app: <https://play.google.com/store/apps/details?id=com.namsung.dualiplug>
- XVM279BT owner's manual: <https://www.dualav.com/wp-content/uploads/2022/01/XVM279BT_72721.pdf>
- Vendor: <https://www.dualav.com/>
- Bluetooth SIG `member_uuids.yaml` (no entry for `0x7544` — the
  leading bytes are ASCII, not a CID allocation)
- Capture: `research/nearsight_export.json`, one unit, three sightings
