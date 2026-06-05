# Amazon Ring (Doorbell / Camera)

## Overview

Amazon Ring is a smart-home video and access ecosystem (Video Doorbells,
Stick Up Cam, Floodlight Cam, Indoor Cam, Spotlight Cam Battery, Alarm
Hub). Battery-powered cameras advertise periodically over BLE for
companion-app discovery, low-power signaling, and Amazon Sidewalk
participation. Ring is an Amazon subsidiary, so the advertisements
carry SIG company ID 0x0171 (Amazon.com Services LLC) plus a
vendor-defined 128-bit service from Ring's own `9760xxxx-…` namespace.

## Supported Models

Any device advertising CID 0x0171 + the Ring vendor service UUID
`9760FACE-A234-4686-9E00-FCBBEE000002` (or a sibling under the same
`9760xxxx-A234-4686-9E00-FCBBEEXXXXXX` template). Captured in the wild
as "Ring 87" — a battery doorbell/camera in companion mode.

The parser does **not** attempt to pin the specific model (Doorbell Pro
vs Stick Up Cam vs Floodlight) because the adv payload layout isn't
publicly documented and the localName encodes only a display suffix,
not a model marker.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | 0x0171 | Amazon.com Services LLC (SIG-registered) |
| Service UUID | `9760FACE-A234-4686-9E00-FCBBEE000002` | Ring vendor 128-bit; not in SIG `member_uuids.yaml` |
| Local name | `Ring <decimal>` (optional) | e.g. `Ring 87`; decimal suffix is a display ID — last byte of the payload tail rendered as decimal |
| Address type | `random` | rotating private address |

A match requires **CID 0x0171 OR the Ring service UUID**. The localName
alone is insufficient because Oura Ring also advertises localName "Ring
\<N\>" (CID 0x02B2, distinct UUID).

### What We Can Parse

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `Amazon Ring` |
| Product family | hard-coded | `Doorbell / Camera` |
| Device class | hard-coded | `doorbell_camera` |
| `device_name` | localName | when present |
| `display_suffix` | localName regex | 1–4 decimal digits after `Ring ` |
| `vendor_service_uuid` | hard-coded | emitted when UUID-matched |
| `payload_hex` | manufacturerPayload | 9-byte tail after CID; opaque |

### What We Cannot Parse from the Advertisement

- Specific Ring product model (Battery Doorbell vs Stick Up Cam vs …).
- Battery level / charge state.
- Motion / live-view state.
- Firmware version.
- Subscribed Ring Protect plan tier.

All live device state requires either the Ring cloud API (with the
user's account) or local-network mDNS discovery. The advertisement only
proves a Ring device is nearby.

## Stable Identity

The decimal `display_suffix` is a per-unit identifier that survives MAC
rotation (the suffix renders the same `Ring N` localName across address
churn). We prefer it over the rotating MAC:

```
stable_key = amazon_ring:suffix:<decimal>
```

When the suffix is unavailable (no localName), fall back to:

```
stable_key = amazon_ring:mac:<mac>
```

## Detection Significance

- A Ring doorbell or camera at a residence is a strong **home-security
  context** clue. Detection is useful for forensic timelines (who was
  on the porch / in the back yard, indirectly).
- Ring participates in **Amazon Sidewalk** — sighting a Ring device is
  also weak evidence that the user's network bridges Sidewalk for
  neighbour devices (e.g., Tile, level locks).
- The "Ring N" naming is shared across the entire fleet of one
  customer's devices — multiple Ring cams nearby with sequential
  suffixes (`Ring 1`, `Ring 2`, `Ring 3`) suggests a multi-camera
  install.

## References

- [BT SIG company identifiers (YAML mirror)](https://bitbucket.org/bluetooth-SIG/public/raw/HEAD/assigned_numbers/company_identifiers/company_identifiers.yaml) — confirms 0x0171
- [Tenable: Inside Amazon's Ring Alarm System](https://medium.com/tenable-techblog/inside-amazons-ring-alarm-system-9731bc519974) — documents sibling service `9760d077-…3373f7`
- [Amazon Frustration-Free Setup / BLE mesh docs](https://developer.amazon.com/docs/frustration-free-setup/bluetooth-mesh-overview.html)
