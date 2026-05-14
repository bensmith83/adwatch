# HTC / Valve Vive Base Station 2.0 ("Lighthouse")

## Overview

The Vive Base Station 2.0 (a.k.a. SteamVR Lighthouse 2.0) is the
infrared sweeping-laser tracker that lights up the play space for
Valve Index, HTC Vive Pro, Vive Cosmos Elite, and most other
SteamVR-compatible headsets. Each station ships a small BLE radio
used for power management — Valve's `lh_console` and community tools
like `lighthouse-v2-manager` and `pyvive2` toggle the station on/off
by writing to a private GATT service over BLE.

The discovery beacon itself is plaintext and continuously broadcast
while the station is awake, so a passive scanner can easily
attribute every base station in a VR room. The parser exposes the
station's stable 6-character ID — the same value Valve's tools use
to address it.

## Identification

```
local_name:    "HTC BS XXXXXX"
               └──┬──┘ └─┬──┘
                  │      └── 6 hex chars — station ID
                  └────────── literal prefix (note: TWO spaces collapsed to one)
service_uuids: ["CB00"]      ← 16-bit Vive Base Station service
```

Regex: `^HTC BS ([0-9A-Fa-f]{6})$`

The parser **requires both** the name pattern and the `0xCB00` service
UUID to match — neither alone is a strong-enough signal (the name
prefix could conceivably collide with other HTC products and `0xCB00`
is not registered in the Bluetooth SIG database, so other DIY devices
could theoretically use it).

`0xCB00` is **not in the official Bluetooth SIG 16-bit UUID
registry**. Valve / HTC ship it as a private-use 16-bit UUID; this is
technically a spec violation (only assigned UUIDs may be advertised
as 16-bit) but it has been stable across all Vive Base Station 2.0
firmware revisions since 2018.

## Station ID

The 6 hex characters at the end of the local name are the last three
bytes of the base station's hardware address — **persistent across
power cycles, reboots, and Steam software updates**. It is also the
identifier Valve's tools print when listing nearby base stations,
e.g.:

```
$ lh-console list
Vive Base Station 25B2DE  state=ON   rssi=-72
Vive Base Station F14AC1  state=ON   rssi=-85
```

`station_id` is the right identity to use for adwatch's
`identifier_hash`:

```
identifier_hash = SHA256("htc_vive_base_station:{station_id}")[:16]
```

## State Inference

Because the beacon is only emitted when the station is powered (the
Lighthouse 1.0 generation goes fully silent in standby), the mere
**presence** of the advertisement means `state = powered_on`.
Inverse-detection (the station is off) is achieved by absence of the
beacon over a long-enough window — adwatch's general device
absence-tracking handles that.

## Generation Detection

Only Base Station 2.0 emits this BLE beacon. The original Lighthouse
1.0 (sold with the launch HTC Vive in 2016) is a passive IR
transmitter with no BLE radio, so it never appears in adwatch.

## What We Cannot Parse

- Channel / frequency the IR sweepers are tuned to
- Sync mode (master / slave / single-station)
- Internal temperature or fan speed (the station does have a fan)
- Power-cycle / standby commands — these flow over an authenticated
  GATT write and are not visible in advertisements.

## Why This Matters

- A passive scan in a VR-equipped office or arcade reveals how many
  rigs are deployed and which ones are currently powered on.
- The 6-char station ID is the same identifier shown in Valve's
  configuration UI, so detections cross-reference cleanly with the
  user's own SteamVR setup if they have access to it.
- Three or more base stations powering on simultaneously is a
  reliable signal that a VR session is starting nearby.

## References

- Valve Lighthouse 2.0 product page: https://www.vive.com/us/accessory/base-station2/
- Community BLE-control project: https://github.com/risa2000/lighthouse-v2-manager
- Python control library: https://github.com/nouser2013/lighthouse-v2-manager
- Pimax / Index integration notes (community): https://github.com/jeroen1602/lighthouse_pm
