# Afero Platform Device Protocol

## Overview

**Afero, Inc.** is not a consumer brand — it is a secure-IoT *platform*
(radio modules, provisioning, cloud) that OEMs embed in their own
products. Afero's own marketing describes its technology as shipping
"inside hundreds of consumer products… lighting, appliances, switches,
fans"; its flagship deployment is **Home Depot's Hubspace** smart-home
line (plugs, bulbs, switches, fans, locks), and Kingfisher's **Myko**
platform in the UK.

So a `0x02D2` sighting reliably means *"an Afero-powered smart-home
device"* and, in North America, most plausibly a Hubspace product — but it
does **not** identify the retail brand or product type. This doc and the
parser both stop at the platform.

## Identifiers

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x02D2` | SIG-assigned to *Afero, Inc.* — unique and uncollidable |
| Frame length | exactly 15 bytes (CID + 13) | 10/10 records |
| Byte 11 | always `0x01` | 10/10 records |
| Address type | random | the BLE address rotates; the payload does not |
| Device class | `smart_home` | |

## Ad Format

```
 0  1 | 2  | 3  4  | 5  6  7  8  9 10 | 11 | 12 13 14
d2 02 | tt | hh hh | MM MM MM MM MM MM | 01 | tail
CID     type  hdr    embedded MAC       const
```

| Bytes | Meaning | Evidence |
|-------|---------|----------|
| 0–1 | CID `0x02D2` (LE `d2 02`) | all records |
| 2 | frame type — `0x03` (7 units), `0x02` (1), `0x01` (2) | |
| 3–4 | 16-bit header, constant per unit, high nibble always `0x8` on types `0x02`/`0x03` | `8f7e`, `823f`, `82d8`, `8360`, `872f`, `8b2c`, `8efb`, `83d4` |
| 5–10 | **6-byte device MAC address** (see below) | 8/8 type-`0x02`/`0x03` records |
| 11 | always `0x01` | 10/10 records |
| 12–14 | `00 00 00` on types `0x02`/`0x03`; per-unit non-zero on type `0x01` | |

### The embedded MAC — how it was confirmed

Bytes 5–10 were suspected to be a MAC because two *different* units shared
their first three bytes. Checking all eight type-`0x02`/`0x03` records
against the IEEE OUI registry resolved **every one** of the six distinct
3-byte prefixes to the same vendor:

| Prefix | OUI owner |
|--------|-----------|
| `A0:DD:6C` | Espressif |
| `C0:CD:D6` | Espressif |
| `EC:C9:FF` | Espressif |
| `A0:A3:B3` | Espressif |
| `F8:B3:B7` | Espressif |
| `34:86:5D` | Espressif |

Eight for eight, all Espressif, all with the locally-administered bit
clear. A random 3-byte field hits *any* registered OUI about 0.2 % of the
time and Espressif specifically far less often, so this is not
coincidence: the frame carries the device's real ESP32 MAC in the clear.
That also independently corroborates the platform reading — Hubspace-class
Afero devices are ESP32-based Wi-Fi + BLE products.

Type `0x01` frames (2 units) do **not** resolve to a registered OUI at
offset 5 (`74:80:77:…`, `ed:ae:84:…`, the latter locally-administered), so
they use a different layout and the parser does not extract a MAC from
them.

## What We Cannot Parse

- OEM brand or retail product (plug vs. bulb vs. fan vs. lock)
- On/off state, dimming level, power draw
- Room / account association
- Firmware version
- Pairing state (frame type `0x01` vs `0x03` may encode it — unproven)

## Identity Hashing

The embedded MAC is stable while the BLE address rotates, so prefer it:

```
if embedded MAC present (frame type 0x02 / 0x03):
    identifier = SHA256("afero:{mac_lower_colon}")[:16]
else:
    identifier = SHA256("afero:{ble_address}")[:16]
```

## Detection Significance

Sightings cluster: ten distinct units were seen in a single residential
capture, which is what a house kitted out with Hubspace plugs/bulbs looks
like. Counting distinct `0x02D2` MACs is a decent proxy for "how much of
this home is on one smart-home platform."

**Privacy note:** the device advertises a randomised BLE address (the
privacy measure) while broadcasting its permanent factory MAC in the
payload (which defeats it). Anyone in range can re-identify these devices
indefinitely, and the MAC is also the device's Wi-Fi identity. This is a
platform-level design choice worth flagging to anyone auditing an
Afero/Hubspace deployment.

## Confidence / Attribution

**High for "Afero platform", deliberately silent on the OEM.** SIG CID
`0x02D2` is Afero's alone; 10 distinct units; a byte layout that is
identical across all of them; and an independently verifiable structural
claim (the embedded MAC resolving to Espressif OUIs 8/8). Hubspace is
named in this doc as the most likely retail context, **not** as a parsed
attribution — the parser reports vendor "Afero, Inc." and nothing more.

## References

- Bluetooth SIG `company_identifiers.yaml` — `0x02D2 = Afero, Inc.`
- IEEE OUI registry (via the nmap `nmap-mac-prefixes` snapshot) — the six
  Espressif prefixes above
- [Afero — Consumer IoT](https://afero.io/html/home/consumer.html) —
  platform scope, "lighting, appliances, switches, fans"
- [Afero / Texas Instruments partnership
  announcement](https://www.businesswire.com/news/home/20260105383252/en/Afero-and-Texas-Instruments-Partner-to-Build-a-Secure-IoT-Platform-Designed-for-a-Connected-World)
  — confirms the Home Depot Hubspace relationship
