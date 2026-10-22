# EssilorLuxottica Nuance Audio Hearing Glasses

## Overview

**Nuance Audio** / **Nuance Audio Plus** are EssilorLuxottica OTC
hearing-assist smart glasses (app `com.essilorluxottica.nuanceaudio`,
Spindox-built, R8-obfuscated). Unlike most glasses, they broadcast a
**structured manufacturer-data frame** under the **Luxottica company ID
`0x0D53`**: product ID, a status byte, an RSSI threshold, a 14-byte ASCII serial
number (on-air population unconfirmed) and a pairing-state bitfield.

The app runs an unfiltered LOW_LATENCY scan and filters in the callback
(`tk1.java:779`, `hy6.java:46-104`).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0D53` (3411) — Luxottica Group S.p.A | Hardcoded `iy6Var.h = 3411` (`tk1.java:742`), logged at `:737`. On air `53 0D`. |
| Local name | "Nuance Audio…" (likely) | Fallback only; exact literal not pinned |
| Service UUID | — | Vendor GATT (`70871E05-…`) is post-connect only |

### Manufacturer data payload (after the CID)

Parser `u34.P` (`u34.java:374-386`), structs `ob5` / `nb5`.

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0 | productId | 1 | uint8 — model/SKU (Audio vs Audio Plus) |
| 1 | frameStatus | 1 | ASCII char; `'P'` (`0x50`) also flags bonding mode |
| 2 | rssiThreshold | 1 | int8 — calibrated proximity threshold |
| 3–16 | serialNumber | 14 | ASCII; only when payload ≥ 17 |
| 17 | pairingState | 1 | bitfield, below |

pairingState: `0x01` alreadyPairedToSmartphone, `0x02`
alreadyPairedToRemoteController, `0x80` (or frameStatus `'P'`) isInBondingMode.

Minimum full frame is 18 payload bytes; shorter frames give defaults. The app
hex-logs up to 30 bytes, so frames may be longer (trailing bytes unparsed).

## What We Can Parse from Advertisements

productId, frameStatus, rssiThreshold, serialNumber, paired-to-phone /
paired-to-remote / bonding-mode flags.

## What Requires GATT

Battery (`0x2A19`), hearing profile, audio settings.

## Identity Hashing

If the serial is populated on air: `SHA256("nuance:{serialNumber}")[:16]`
(survives MAC randomization). Otherwise fall back to MAC.

> **Confidence caveat (from the report's Stage 5b audit, batch27):** the
> serial-on-air claim is **PENDING RUNTIME — not confirmed**. Static analysis
> proves the app *parses* a serial, not that the device *emits* one. The
> device-class fingerprint (CID `0x0D53` frame) is upheld at MEDIUM. Byte
> layout confidence is HIGH.

## Detection Significance

- Device-class leak = probable hearing impairment of the wearer.
- pairingState reveals active use vs idle, and open bonding windows.
- productId leaks product tier.

## adwatch Status — plugin conflict

`src/adwatch/plugins/smart_glasses.py` already matches CID `0x0D53` and labels
it "Luxottica (Meta Ray-Ban manufacturer)". Per this report, **`0x0D53` is also
used by Nuance Audio hearing glasses**, so today those adverts are attributed to
smart glasses generically / implied Ray-Ban. A future change should decode the
frame above (≥ 18 bytes, ASCII serial at 3–16) and label it Nuance Audio, and
stop implying Ray-Ban for `0x0D53` alone. Not implemented here (docs only).

## References

- apk-ble-hunting `reports/essilorluxottica-nuanceaudio_passive.md` (and
  `reports/essilorluxottica-nuanceaudio.md`, `reports/_audit_batch27.md` §F)
- Code cited by the report: `tk1.java:737-779`, `hy6.java:46-104`,
  `iy6.java:38`, `u34.java:374-386`, `ob5.java`, `nb5.java`, `nt.java:41-47,440`
