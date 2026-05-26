# Sleep Number (Select Comfort) Smart Beds

## Overview

Sleep Number (formerly Select Comfort) ships smart beds with a BLE
radio used by their app to set firmness, raise/lower the head/foot,
read sleep score, etc. The radio is on whenever the bed is powered,
so a passive scan in a bedroom will pick the bed up continuously —
in our captures it was the single most-frequent unparsed device
(168 sightings in one home).

The advertisement is identification-only. Live state (firmness,
position, occupancy, sleep score) lives behind Sleep Number's MCR
binary GATT protocol and requires a connection.

Two firmware generations are both handled here:

| Generation | Service UUID | `firmware_family` label |
|------------|--------------|-------------------------|
| Legacy MCR / BAM | `FFFFD1FD-388D-938B-344A-939D1F6EFEE0` | `MCR (legacy)` |
| Fuzion / Climate360 / FlexFit Smart | `09D23FAE-90E6-44C2-95B6-0B3D0F1ABF25` | `Fuzion (Climate360 / FlexFit Smart)` |

If a unit ever advertises both UUIDs simultaneously, we tag as Fuzion —
it's the higher-capability firmware and we'd rather over-report
capability than miss it.

## Identification

| Signal | Value | Firmware | Notes |
|--------|-------|----------|-------|
| OUI | `64:DB:A0` | both | IEEE registry: "Select Comfort" |
| Mfg-data header | `53 4E` ("SN" ASCII) | MCR | NOT a SIG-assigned company ID (0x4E53 is unallocated) |
| Service UUID | `FFFFD1FD-388D-938B-344A-939D1F6EFEE0` | MCR | Sleep Number legacy MCR service |
| Service UUID | `09D23FAE-90E6-44C2-95B6-0B3D0F1ABF25` | Fuzion | Climate360 / FlexFit Smart service |
| Local name | Literal MAC string (e.g. `64:db:a0:f7:2b:ff`) | both | Firmware exposes its own MAC as the friendly name |
| Local name | `Smart bed XXXXXX` (6-hex MAC suffix) | Fuzion | Friendlier label used by Fuzion firmware |

Any single signal is sufficient to identify the device; combinations
are unambiguous. The Fuzion service UUID is also used to disambiguate
firmware family when only the UUID is present.

## Wire Format

```
53 4E | 92 06 00 00 00
└──┬─┘ └─────┬────────┘
   │         └── 5-byte firmware-version / flags marker (unconfirmed)
   └────────── "SN" ASCII magic header
```

The 5 bytes after `SN` are **identical across all devices and
sightings in our captures**, so they're presumed static identity /
firmware-family markers rather than dynamic state. They're surfaced
verbatim as `firmware_marker_hex` for later differential analysis if
a unit with different bytes is ever seen.

| Offset | Bytes | Field |
|--------|-------|-------|
| 0–1    | `53 4E` | ASCII "SN" magic (fixed) |
| 2      | `92`    | Unknown — likely version / flag byte (high bit set) |
| 3      | `06`    | Unknown — likely subtype |
| 4–6    | `00 00 00` | Reserved / padding |

## Identity Hashing

```
identifier_hash = SHA256(mac_address)[:16]
```

The BLE MAC is sufficient for identity because (a) Sleep Number
beds are stationary, and (b) we have no broadcast device-id field
to derive a MAC-rotation-stable key from. If we ever observe MAC
rotation on these beds in practice, swap to the trailing 5-byte
marker once it's been confirmed to vary per unit.

## Captured Examples

```
# Legacy MCR (our capture set, 2 distinct units)
local_name=64:db:a0:f7:2b:ff   svc_uuid=FFFFD1FD-…   mfr=53 4E 92 06 00 00 00
local_name=64:db:a0:??:??:??   svc_uuid=FFFFD1FD-…   mfr=53 4E 92 06 00 00 00  (second unit, identical mfg bytes)

# Fuzion (from kristofferR/ha-adjustable-bed reference fixtures)
local_name="Smart bed 0074E7"  svc_uuid=09D23FAE-…   mfr=(none)
```

168 + 8 MCR sightings across two distinct devices in a single
household capture; Fuzion sample is from the reference fixtures, no
Fuzion units in our own capture set yet.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Manufacturer | UUID / "SN" magic | Sleep Number (Select Comfort) |
| Firmware family | UUID | `MCR (legacy)` or `Fuzion (Climate360 / FlexFit Smart)` |
| Firmware marker | mfr[2..7] | MCR only — raw hex, decoding unconfirmed |
| MAC suffix | local name `Smart bed XXXXXX` | Fuzion only — last 3 MAC bytes |
| Device class | derived | `smart_bed` |

## What Requires GATT Connection

- Current firmness (0–100 sleep-number)
- Head / foot position
- Bed occupancy
- Sleep-score history
- Massage / warming feature state
- Climate360 footwarmer / cooling state (Fuzion)

All of the above are documented in the open-source projects below
and require an authenticated write to the bed's control characteristic
followed by reading back the binary response.

| Firmware | Control characteristic | Reference |
|----------|------------------------|-----------|
| MCR | proprietary `0x16 0x16` sync + Fletcher CRC | `JonGilmore/sleepnumber-ble` |
| Fuzion | BamKey `421e00f3-ae76-4c49-ab6e-39e4df4a5333`, `fUzIoN` ASCII preamble | `kristofferR/ha-adjustable-bed` |

## References

- IEEE OUI registry — `64-DB-A0` → Select Comfort
- `JonGilmore/sleepnumber-ble` — legacy MCR firmware GATT protocol
  docs (the source for the legacy UUID + MAC-as-name confirmation)
- `kristofferR/ha-adjustable-bed` — Fuzion / Climate360 / FlexFit
  Smart firmware (`docs/beds/sleep_number.md` enumerates the Fuzion
  service + characteristic UUIDs and the `fUzIoN` payload preamble)
- Home Assistant community thread: "Custom integration: local
  bluetooth control for sleepnumber beds" — independent SleepIQ
  Android-app reverse-engineering corroborating the Fuzion UUIDs
