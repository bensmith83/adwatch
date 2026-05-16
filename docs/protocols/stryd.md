# Stryd Running Power Meter

## Overview

**Stryd** is a shoe-mounted footpod that measures running power, pace,
distance, cadence, and ground-contact / form metrics in real time.
Unlike most fitness wearables, it acts as a **dual-profile BLE
peripheral**: it simultaneously advertises both the standard
**Cycling Power Service** (`0x1818`) and the **Running Speed and
Cadence Service** (`0x1814`), so any cycling head unit or running
watch can pick up the metric it cares about.

The footpod runs continuously and pairs to multiple receivers
(Garmin watches, Apple Watch, Zwift, TrainerRoad, etc.) over BLE +
ANT+ in parallel.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0xAAAA` | Non-compliant — `0xAAAA` is not an assigned BT SIG vendor ID; Stryd uses it as a self-chosen marker |
| Service UUIDs | `0x1818` + `0x1814` + `0x180A` | Cycling Power + Running Speed/Cadence + Device Information |
| Local name | `Stryd`, `Stryd5`, `StrydX`, `Stryd Duo`, … | Model-suffixed |

Captured in adwatch research export:

```
Local name: "StrydX"
Mfr data:   aa aa 5b 47 00 2a 40 df
            └─┬─┘ └─────────┬───────┘
             cid     payload (6 bytes, opaque)
Svc UUIDs:  [1818, 1814, 180A]
```

A reliable match is **local name has `Stryd` prefix** AND (any one of:
the `0xAAAA` mfr-data prefix, the cycling-power service, or the
running-speed service). Name alone is not enough — generic "stryd"
strings could appear in unrelated devices.

## Manufacturer Data

| Offset (post-cid) | Bytes        | Meaning |
|-------------------|--------------|---------|
| 0                 | `5B`         | Likely protocol / frame-type byte |
| 1                 | `47`         | Status / battery flags |
| 2–5               | `00 2A 40 DF`| Opaque (device serial fragment? frame counter?) |

The mfr-data payload changes between firmware revisions. The parser
exposes it as `payload_hex` for forensic comparison and does not
attempt to decode beyond the company-ID prefix.

## Live Metrics (Out of Scope for Passive Scanner)

The interesting data — power in watts, ground-contact time, vertical
oscillation, leg-spring stiffness, etc. — is delivered via **GATT
notifications** on the Cycling Power characteristic, with Stryd-
specific fields packed into the vendor-extension area of the standard
CPS Measurement format. adwatch's passive scanner does not connect
GATT, so live power numbers are not available — only **presence and
identity** of the footpod.

## Identity Hashing

```
identifier_hash = SHA256("stryd:{model}:{mac_address}")[:16]
```

Stryd uses a stable BLE MAC (verified across multi-week captures —
they have no incentive to rotate, as ANT+ pairing depends on a stable
device ID and the BLE-only privacy model would break Zwift's connect-
on-discover flow).

## Privacy Note

Stryd advertises continuously while powered on (it has a small
internal battery that lasts ~20h between USB charges). A runner with a
Stryd in their shoe can be passively tracked across locations via the
fixed MAC and the distinctive `Stryd`-prefixed local name. This is
comparable to a non-rotating BLE HRM strap.

## What We Cannot Parse Without GATT

- Running power (W) — the headline metric
- Form: ground-contact, vertical oscillation, leg-spring stiffness
- Pace and distance (live)
- Cadence (steps per minute)
- Battery percentage

All require a paired GATT session against the Cycling Power and
Running Speed/Cadence characteristics.

## References

- Stryd product page: https://www.stryd.com
- Stryd hardware FAQ: https://help.stryd.com/en/articles/8977365-stryd-hardware-common-questions
- Garmin pairing names "FP - StrydX or Stryd5" and "PWR - StrydX or Stryd5": https://help.stryd.com/en/articles/8903411-configuring-your-garmin-watch-to-take-pace-distance-from-stryd-other-sensor-pairings
- BT SIG Cycling Power Service `0x1818`: https://www.bluetooth.com/specifications/specs/cycling-power-service-1-1
- BT SIG Running Speed and Cadence Service `0x1814`: https://www.bluetooth.com/specifications/specs/running-speed-and-cadence-service-1-0
