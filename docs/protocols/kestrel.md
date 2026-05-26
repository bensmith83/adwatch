# Kestrel Weather Meters (Nielsen-Kellerman)

## Overview

Nielsen-Kellerman (NK) makes the **Kestrel** line of handheld and
fixed weather meters — pocket-sized instruments used by snipers,
firefighters, athletes, agricultural pros, etc. Higher-end models
(5500, 5700 series and up) include BLE for live telemetry to the
Kestrel-LiNK app or partner integrations.

The advertisement carries the device serial in the local name and
a small sample counter at the end of the manufacturer-data
payload. The middle of the payload has full per-byte entropy and
is **presumed AES-encrypted** — Kestrel-LiNK uses PIN-paired
session keys, and NK gates third-party access behind an SDK NDA
(`techsupport@nkhome.com`), so live values (wind, temp, RH,
pressure, etc.) require either a paired GATT session or the
licensed Kestrel-LiNK SDK.

This parser is **identification-only**: it surfaces vendor,
serial, presumed product family, and the sample counter (useful
for de-duping rapid sightings of the same broadcast).

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID | `C74EDD21-763C-4E54-85A8-43BB75035D75` | Kestrel custom service — primary anchor |
| Local name | `K######` (handheld) or `c######` (alternate FW) | Device serial; standard NK convention is `K4500-XXXXXX` but BLE truncates to 7-char serial |
| Mfg-data header | `00 06 …` | **NOT** a SIG company ID for NK — `0x0006` is Microsoft; NK's CID is `0x00EA`. The `00 06` here is internal padding/framing, not a CID. |

The Bluetooth SIG company-id is misleading — **do not** filter by
`companyID == 0x0006`, because Microsoft owns that ID and a true
NK CID would be `0x00EA`. The custom service UUID is the only
reliable anchor.

## Wire Format

Twenty bytes of manufacturer data, framed as:

```
00 06 | 4a 8a 71 e7 c2 7b 30 1b b8 92 1d fe c3 17 55 84 | 00 09
└──┬─┘ └───────────────────────────┬────────────────────┘ └──┬─┘
   │                               │                          └── sample counter (BE u16)
   │                               └── 16-byte encrypted payload (presumed AES)
   └── 2-byte leading framing (constant `00 06` in all captures)
```

| Offset | Bytes | Field | Confidence |
|--------|-------|-------|-----------|
| 0–1    | 2 | Fixed header `00 06` | High (stable across all captures) |
| 2–17   | 16 | Encrypted live telemetry | Medium (inferred from entropy + documented PIN-pairing) |
| 18–19  | 2 | Sample counter (BE u16) | Medium (only 2 samples — `0x0009`, `0x0019`) |

The 16-byte middle blob is decoded byte-by-byte unique in both
sampled devices, consistent with AES-encrypted payload (a
24-byte/16-byte AES block is plausible). Without the session key
(provisioned at PIN pairing) the bytes cannot be decoded.

## Local Name Decoding

```
"K151020"
 │ └─┬──┘
 │   └── 6-digit unit serial
 └────── Product / firmware-family prefix letter
```

In NK's official documentation the BLE name is `<Model>-<Serial>`
(e.g. `K4500-677561`), but devices in our captures broadcast only
the 7-char serial without the dash. Why isn't documented; possible
explanations are (a) short-name truncation at scan time, (b) older
firmware revisions used a serial-only name, or (c) the device only
exposes the full `<Model>-<Serial>` form on a paired connection.

Observed prefix letters:

| Prefix | Family (inferred) |
|--------|-------------------|
| `K` | Kestrel handheld (standard) |
| `c` | Kestrel alternate firmware (unverified — could be DROP or older line) |

Other prefixes pass through as `Kestrel (alternate firmware)`.

## Identity Hashing

```
identifier_hash = SHA256(serial)[:16]      # preferred — stable per unit
identifier_hash = SHA256(mac_address)[:16] # fallback when local name absent
```

The serial in the local name is stable per physical unit and
survives BLE MAC rotation, so it's the right key for cross-session
identity.

## Captured Examples

```
K151020   svc=C74EDD21-…   mfr= 00 06 4a8a71e7c27b301bb8921dfec3175584 0009
c975020   svc=C74EDD21-…   mfr= 00 06 69ba7162b09c4a9f91761edc4368e1d2 0019
```

55 sightings across 2 distinct units in our test capture.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Manufacturer | UUID | Nielsen-Kellerman |
| Product family | name prefix | Heuristic — `K`=handheld, others=alternate |
| Serial | local name | Stable per unit |
| Sample counter | mfr[18..20] | Useful for de-dup |
| Encrypted payload | mfr[2..18] | Surfaced verbatim for future decoding work |

## What Requires GATT + Session Key

- Wind speed, max wind, average wind
- Air temperature
- Wind chill / heat index
- Relative humidity
- Barometric pressure
- Density altitude
- Compass / wind direction
- Battery state

Decoding the encrypted advertisement bytes is also gated on the
session key — those bytes are likely a redundant copy of recent
state for app-launch latency, but without the key they're opaque.

## References

- Kestrel-LiNK BLE pairing PDF (`kestrelinstruments.com` — confirms
  custom service UUID and the `<Model>-<Serial>` name convention)
- `kestrelmeters.com/pages/software-partners` — NK's developer
  contact; full SDK requires an NDA (email `techsupport@nkhome.com`)
- `mighkel/ATAK-Plugin-KestrelWx` — third-party plugin; binary-only,
  source not published
- IEEE OUI registry — `00-06-66` (Roving Networks / Microchip RN
  series) is the BLE module family NK ships on Kestrel units
- Bluetooth SIG company-id list — confirms `0x0006` is Microsoft,
  not NK (NK's CID is `0x00EA`)
