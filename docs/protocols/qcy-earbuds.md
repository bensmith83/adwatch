# QCY Earbuds Plugin

## Overview

**QCY** is a Hong-Kong-listed Chinese consumer-audio brand selling sub-$50 true-wireless earbuds (T13, MeloBuds, MeloBuds Pro/ANC, H3, HT05, HT18, AilyBuds, AilyBuds Clear/Pro+, Arcbuds, …). QCY units are built on Airoha and BES (Bestechnic) BLE chipsets across SKUs and pair with the **QCY+** mobile companion app on iOS / Android.

This parser identifies a QCY earbud while it is broadcasting in **app-pairing mode** — i.e. waiting for the QCY+ app to add it as a new device. In that mode the firmware emits a very specific 3-signal fingerprint that lets us classify it without relying on any single shared identifier.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|---|---|---|
| Manufacturer-data CID | `0x521C` (little-endian wire `1c 52`) | **Not** SIG-assigned. Vendor-vanity marker emitted by QCY firmware. ASCII reading of the two bytes is `'\x1cR'`. |
| Service UUID (16-bit) | `FEE8` | SIG-allocated. Historically Quintic Corp / NXP; now widely re-used by many Chinese OEMs, **not unique to QCY**. |
| Local name | `QCY-APP` | Broadcast by an unpaired QCY earbud waiting for the QCY+ app's pairing handshake. |
| Manufacturer payload | 24 bytes after CID | Trailing 6 bytes look MAC-like (best-effort embedded MAC extraction). |

We require **at least two of the three signals** to be present. FEE8 alone is shared across many vendors; CID 0x521C alone is unattributed in the SIG registry; the `QCY-APP` name alone is trivially spoofable. Two-of-three is the conservative fingerprint that avoids false positives.

### Manufacturer Payload Layout (24 bytes after CID)

Example real capture: `1c52` `4a737c006e646400a2ced6ac8460a2ced600a9d376aebede`

| Offset | Bytes | Likely meaning |
|---|---|---|
| 0–7 | `4a 73 7c 00 6e 64 64 00` | Stable prefix across observed captures; probably a firmware/family marker or pairing-token header. |
| 8–13 | `a2 ce d6 ac 84 60` | Looks MAC-like; possibly the earbud's Classic Bluetooth MAC (case half) or a paired-host hint. |
| 14–17 | `a2 ce d6 00` | Repeats the first 3 bytes of the previous group + a sentinel. Unconfirmed. |
| 18–23 | `a9 d3 76 ae be de` | Looks MAC-like; we expose this as `embedded_mac` and use it as the stable key. **Best-effort** — confirm against more captures. |

We surface the full payload as `payload_hex` so the user can confirm the layout across additional units, but we do not gate identification on any specific byte pattern.

### Stable Key

When the payload is long enough to extract the trailing 6 bytes, the parser sets `stableKey = "qcy:<embedded_mac>"`. If the payload is shorter (or absent — e.g. matched on FEE8 + QCY-APP name only), `stableKey` is `nil` and the parser still emits a `ParseResult` keyed off the BLE MAC.

## Metadata Surfaced

| Key | Value |
|---|---|
| `vendor` | `QCY (Hong Kong-listed audio brand)` |
| `pairing_app` | `QCY+` |
| `vendor_cid_hex` | `0x521C` (when CID matched) |
| `matched_service_uuid` | `FEE8` (when service UUID matched) |
| `device_name` | `QCY-APP` (when local name matched) |
| `app_pairing_mode` | `true` (when local name matched) |
| `payload_hex` | full 24-byte payload after the CID |
| `embedded_mac` | trailing-6-byte best-effort MAC (e.g. `a9:d3:76:ae:be:de`) |

## Examples

| Capture | Inference |
|---|---|
| CID 0x521C + FEE8 + name `QCY-APP` (real capture) | full match, `embedded_mac` extracted, `stableKey = "qcy:a9:d3:76:ae:be:de"` |
| CID 0x521C + name `QCY-APP` (no FEE8) | match, `app_pairing_mode = true` |
| CID 0x521C + FEE8 (no name) | match, `app_pairing_mode` absent |
| CID 0x521C only | nil — too risky (unattributed CID alone) |
| FEE8 only | nil — FEE8 is shared across vendors |
| `QCY-APP` name only | nil — name alone is spoofable |

## References

- [QCY Official site](https://www.qcy.com/)
- [QCY T13 Support](https://www.qcy.com/pages/support-center-t13)
- [QCY MeloBuds Pro Support](https://www.qcy.com/pages/support-center-melobuds-pro)
- [Bluetooth SIG Company Identifiers](https://www.bluetooth.com/specifications/assigned-numbers/company-identifiers/) — 0x521C is **not** in the SIG registry (confirmed 2026-05 against Nordic's `bluetooth-numbers-database` mirror)
- [Airoha RACE SDK background](https://insinuator.net/2025/12/bluetooth-headphone-jacking-full-disclosure-of-airoha-race-vulnerabilities/) — many QCY SKUs ship Airoha chips; QCY's BLE-only "QCY-APP" advertising is **distinct** from the Airoha RACE service UUID, so this parser is independent of `AirohaAudioParser`.
