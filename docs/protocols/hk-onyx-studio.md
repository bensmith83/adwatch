# Harman Kardon Onyx Studio (Richsound OEM)

## Overview

The Harman Kardon **Onyx Studio** is a series of portable Bluetooth
speakers (Onyx Studio 1 through 8 at time of writing). The hardware
is built by **Zhong Shan City Richsound Electronic Industrial Ltd.**
under contract to Harman International; the BLE advertisement
therefore carries Richsound's Bluetooth SIG company ID
(`0x0ECB`), **not** any of Harman's three CIDs
(`0x0057`, `0x009E`, `0x075A`).

The advertisement is identification-only — the speaker exposes a
user-facing local name and a short, presumed-static company-data
payload while it is powered. Live state (volume, source, battery,
HK Connect+ mesh group) lives behind Harman's proprietary HK Connect
app GATT surface and is not documented publicly.

## Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0ECB` | "Zhong Shan City Richsound Electronic Industrial Ltd." — the OEM, not Harman |
| Local name | `HK Onyx Studio N` or `HK Onyx BT` | `N` is the model number (1–8 today); `HK Onyx BT` shows up in some pairing-mode states |

The parser matches on **either** signal, but the local-name regex is
what makes the result product-specific. The bare `0x0ECB` CID also
covers other Richsound-OEM products (e.g. some JBL CM-series
commercial speakers), so without a matching name we should not claim
"Onyx Studio".

### CID gotchas

Harman has three legitimate SIG-assigned CIDs:

| CID | Holder |
|-----|--------|
| `0x0057` | Harman International Industries, Inc. |
| `0x009E` | Bose Corporation **— not Harman, but adjacent confusion** |
| `0x075A` | HARMAN CO., LTD. |

`0x0065` is what older firmware on JBL/Bose products advertises (the
existing `BoseParser` keys on it); the Onyx Studio 4 we observed in
the wild does **not** use any of these — it uses Richsound's
`0x0ECB`. Don't try to match HK Onyx by Harman's CID; you'll miss it.

## Wire Format (post-CID payload)

```
HK Onyx Studio 4 capture
mfr_hex = cb 0e | e5 1e 01 00 09 03
          └─┬─┘ └─────────┬────────┘
           CID         6-byte payload (presumed static identity)
```

Per-byte best-guess interpretation (unverified — single-unit capture):

| Offset | Bytes | Speculation |
|--------|-------|------------|
| 0–1    | `e5 1e` | Model / SKU code (looks like a fixed 2-byte tag, LE `0x1ee5`) |
| 2–3    | `01 00` | Version / capability flag pair (LE `0x0001` — possibly "HK Connect+ enabled") |
| 4      | `09`    | State byte — pairing / discoverable mode |
| 5      | `03`    | Counter / sub-state |

We surface bytes 0–5 verbatim as `payload_hex` until we have a
multi-unit capture set to deduce field boundaries. All six bytes
were identical across every sighting of one unit in our capture —
consistent with a static identity / SKU tag rather than dynamic
telemetry.

### Research status (2026-05-25)

A targeted web-research pass found **no public reverse-engineering**
of these six bytes — no GitHub project, blog post, Hackaday
write-up, Discord thread, or btsnoop capture documents the
post-CID payload for HK Onyx Studio. The closest existing
project (`jiwandono/harman-kardon-onyx-studio-3`) is purely a
hardware / CSR8675 chip teardown with zero BLE-advertising
content. Harman's HK Connect app is the only ground-truth source
for the format and remains undecompiled in the public corpus.

To make progress here we would need either:

1. Captures from 2+ different Onyx Studio model numbers to diff
   the leading 2 bytes (`e5 1e` is our model-code hypothesis).
2. Sustained captures from a single unit (5+ samples over a minute)
   to identify any varying counter / battery byte.
3. APK decompilation of `com.harman.connectplus` (HK Connect) to
   extract the advertisement parser directly.

None of these are blocking for identification — `payload_hex` is
sufficient for the diff-and-alert use case the rest of the app
operates on.

## Identity Hashing

```
identifier_hash = SHA256("{local_name}")[:16]   # when name present
identifier_hash = SHA256(mac_address)[:16]      # fallback
```

The Onyx Studio appears to advertise a stable BLE MAC and an
unchanging local name; either is fine as an identity anchor. We
prefer the local name because (a) it survives a paired-MAC change
on iOS and (b) the speaker is a stationary household appliance.

## Captured Examples

```
local_name="HK Onyx Studio 4"  mfr=cb 0e e5 1e 01 00 09 03   svc_uuid=(none)
```

25 sightings across one unit in a single household capture.

## What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Manufacturer | CID lookup | "Harman Kardon (via Richsound OEM)" |
| Product family | local name | "Onyx Studio N" or "Onyx (BT pairing)" |
| Model number | local name regex | `N` digit (1–8) when present |
| Device class | derived | `speaker` |
| Payload hex | mfg bytes 2..7 | Six bytes, decoding unconfirmed |

## What Requires GATT Connection

- Battery level
- Volume / EQ
- Current Bluetooth source
- HK Connect+ mesh-group membership
- Firmware version

All of the above live behind Harman's HK Connect app GATT protocol,
which is not publicly documented and not handled here.

## References

- Bluetooth SIG assigned numbers (company identifiers) —
  `0x0ECB → Zhong Shan City Richsound Electronic Industrial Ltd.`
- Harman support: "How do I use the HK Connect feature on the Onyx
  Studio 4" (confirms the `HK Onyx …` local-name convention)
- Richsound corporate page (richsound.com) — confirms ODM
  relationships with Harman and JBL
- IEEE OUI registry (no Onyx-specific OUI assignment — the MAC is
  randomized per-pairing on iOS captures)
