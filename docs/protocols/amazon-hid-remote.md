# Amazon HID Remote Plugin

## Overview

Bluetooth SIG company ID `0x0171` is registered to **Amazon Fulfillment Service** (Amazon Lab126's BT-product entity, formerly "Amazon.com Services, Inc."). Amazon's Bluetooth HID accessories — Fire TV Voice Remote, Fire TV remote (3rd gen +), Echo Buttons, and various Lab126 prototyping radios — advertise under this CID together with the SIG-standard HID-over-GATT service `0x1812`.

This parser is distinct from `AmazonFireTVParser`, which keys off Amazon's separate service-data UUID `0xFE00` broadcast by Fire TV streamers themselves. The remote-control accessory side of the same ecosystem uses CID `0x0171` + service `0x1812` instead.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Company ID | `0x0171` (Amazon Fulfillment Service / Lab126) |
| Service UUID | `0x1812` (HID-over-GATT, SIG-standard) |
| Local name | short marketing token (e.g. `"AR"` for the Fire TV "Alexa Remote" line) |
| Address type | random (rotates per pairing session) |

We require **both** the CID and the HID service UUID to match — gating on CID alone would over-match Amazon's wide product range, and gating on `0x1812` alone would over-match every BT HID device (keyboards, mice, game controllers). The intersection is highly specific.

### Manufacturer Data Layout (4 bytes total, 2-byte payload)

```
71 01 | XX YY
──┬── ──┬─┬──
 CID  flags? per-device
LE 0x0171   tag / state byte
            (XX varies, YY varies)
```

Observed in the wild: `71 01 04 21` — CID + 2 payload bytes. The two payload bytes are not publicly documented; they appear to encode HID device sub-type (byte 2) and a per-emitter / state byte (byte 3). We surface them as `payload_hex` so they remain inspectable without speculating about semantics.

### Local Name

Short marketing tokens identify the product line:

| Local name | Product line |
|---|---|
| `AR` | Fire TV "Alexa Remote" family (3rd-gen Voice Remote, Voice Remote Pro) |

Other Amazon HID accessories advertising under CID `0x0171` may use different short names; we surface whatever name is broadcast as `device_name` and additionally annotate `product_family` only when the name is in the table above.

### Stable Key

```
amazon_hid:<mac>
```

The advertised BD_ADDR is random per pairing, so the stable key falls back to MAC-scoped. There is no payload-recoverable serial.

## Detection Significance

- **High-confidence vendor.** SIG-assigned CID `0x0171` is unique to Amazon Lab126 / Fulfillment Service.
- **Distinguishes remotes from streamers.** Together with `AmazonFireTVParser` (FE00 service-data) and `AmazonEchoParser` (Echo-specific service-data), this parser separates the *remote-control* accessory class from the streamer / smart-speaker hardware on the same brand.
- **Useful in indoor scans.** A bare HID remote sitting on a coffee table is a strong indicator that a Fire TV (or other Amazon TV-class device) is nearby.

## What We Cannot Parse

- **Exact product model.** The 2-byte payload's semantics are not documented and the local name is too short to disambiguate every SKU. We surface the payload raw for future reverse engineering.
- **Battery / button state.** All telemetry is in the HID-over-GATT characteristics, not in the advertisement.

## References

- [Bluetooth SIG company identifiers](https://www.bluetooth.com/specifications/assigned-numbers/) — `0x0171` = Amazon Fulfillment Service
- [Bluetooth HID-over-GATT (0x1812) — Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/)
- [Amazon Developer — Fire TV remote-control input](https://developer.amazon.com/docs/fire-tv/remote-input.html)
- `research/adwatch_export 6.json` — one captured "AR" device
