# Hubble Network — BLE IoT Beacon (service UUID FCA6)

## Overview

[Hubble Network](https://hubblenetwork.com/) operates a low-power IoT
network in which small devices broadcast short BLE advertisements that are
relayed either by Hubble's own satellites (a custom BLE-derived PHY) or by
phones and gateways running the Hubble Gateway SDK — the same crowd-relay
model as Tile / Find My, but sold as a generic IoT backhaul for asset
trackers, sensors and OEM modules. Devices are built on the public
[`hubble-device-sdk`](https://github.com/HubbleNetwork/hubble-device-sdk)
(Zephyr, ESP-IDF, TI CC23xx/CC27xx, Silicon Labs and Nordic ports), and the
frame they advertise is decoded by Hubble's own open-source scanner,
[`pyhubblenetwork`](https://github.com/HubbleNetwork/pyhubblenetwork). The
parser below decodes exactly what that scanner reads without the device key.

First captured in the 2026-08-26 telemetry sweep: two units, one sighting
each, ~3 h apart on 2026-08-25, random addresses, no local name.

## Satellite PHY (bench-confirmed 2026-10-07)

The frame documented below is the **terrestrial** (BLE advertisement) path. The
**satellite** uplink is a separate, non-BLE waveform the SDK drives on the same
2.4 GHz radio: a narrowband 2-FSK signal (~125 sym/s, native sample rate
781.25 kHz) that hops a 19-channel plan (~25.9 kHz spacing, Nordic synth step)
near **2.482754875 GHz**, wrapped in Reed-Solomon FEC. Captured off-air from an
nRF54L15 with a HackRF and decoded with
[`hubble-satnet-decoder`](https://github.com/HubbleNetwork/hubble-satnet-decoder):

| Field | Value (one captured packet) |
|-------|-----------------------------|
| PHY version | 1 |
| chipset (from synth step) | Nordic (meas. 488.46 Hz vs 488.28) |
| network id | `0x7EE37B21` |
| sequence | 130 |
| auth tag | `0xABC42A5B` |
| channel / hop-seq index | 8 / 1 (of 4 sequences x 19 channels) |
| FEC | Reed-Solomon RS(23,13) |

Phones and ordinary BLE scanners **cannot** see this - it is not an
advertisement. Only a ground SDR (HackRF/Pluto/bladeRF) receives it, and the
transmitting SoC family is identifiable from the synthesizer resolution before a
single byte is decrypted. Out of scope for the passive BLE parser; documented
here for completeness.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service UUID (16-bit list) | `0xFCA6` | Bluetooth SIG member UUID: **Hubble Network Inc.** — `HUBBLE_BLE_UUID` in `include/hubble/ble.h`; the SDK requires it in the complete 16-bit service list |
| Service data | under `0xFCA6` | the network frame; `hubble_ble_advertise_get()` output, AD type `0x16` |
| Company ID | none | no manufacturer-specific data |
| Local name | none | legacy advertising PDU, scannable, no scan-response name |
| Address | random | rotated by the stack; the TI sample uses `PEER_ADDRTYPE_RANDOM_OR_RANDOM_ID` |

One SIG registration (the member UUID) plus a vendor-published frame layout
that the captured bytes fit exactly — a HIGH-confidence attribution to
Hubble Network as the *network*. Which product sits behind the frame (a
tracker, a sensor, a module in someone else's device) is not identifiable:
the SDK is generic and the payload is encrypted.

### Frame layout

`include/hubble/ble.h` defines a fixed header of `HUBBLE_BLE_ADV_HEADER_SIZE
= 12` bytes (the 2-byte UUID prefix, the "device address" and the
authentication tag) plus up to `HUBBLE_BLE_MAX_DATA_LEN = 13` bytes of
caller data — at most 25 bytes of service data including the UUID, i.e. 23
bytes after it, which is what both captures carry. The byte map comes from
`pyhubblenetwork/src/hubblenetwork/ble.py` (`_make_packet`) and
`packets.py`; the 6-bit protocol version is `byte0 >> 2`.

**Version 0 — AES-CTR (both captures):**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–1 | version (6 bits) \| sequence number (10 bits) | 2 | big-endian; `seq = BE16 & 0x3FF` |
| 2–5 | EID | 4 | the rotating "device address"; rotation period = `CONFIG_HUBBLE_EID_ROTATION_PERIOD_SEC` (default **86400 s / daily**; the TI reference sample sets 180 s). Confirmed daily on the Zephyr `ble-network` sample with the UNIX_TIME counter: EID = f(⌊unix/86400⌋), unchanged within a UTC day, so BLE-address rotation gives no intra-day unlinkability. The 4-byte tag is a CMAC over the **ciphertext only** (not time or location) |
| 6–9 | authentication tag | 4 | AES-CMAC-style tag under the device key |
| 10– | ciphertext | 0–13 | customer payload, AES-CTR under the per-device key Hubble provisions |

**Version 1 — plaintext:**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0–4 | version (6 bits) \| network id (34 bits) | 5 | big-endian 40-bit header |
| 5– | customer payload | 0–18 | plaintext |

**Version 2 — AES-EAX:**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| 0 | version | 1 | `0x08` |
| 1–2 | nonce salt | 2 | random per message |
| 3–10 | EID | 8 | little-endian uint64 |
| 11–(n−5) | ciphertext | 0–9 | |
| (n−4)–(n−1) | authentication tag | 4 | AEAD tag |

### Examples (real bytes)

```
03 1e | 7a 3d 44 34 | 05 30 ee cb | ea cd 80 8f 4b 9f 08 45 b9 92 ff 06 b5
v0 seq  EID           auth tag      13-byte ciphertext           (seq 798)

03 87 | 66 40 08 91 | e8 84 90 c2 | b7 9a 1d 22 4a 6d fb ec ec 14 7d b6 a0
v0 seq  EID           auth tag      13-byte ciphertext           (seq 903)
```

Both frames use the maximum 13-byte data length, so these are devices
sending a full application payload (a sensor reading or a status word),
not empty presence beacons.

## Parser Scope (passive-only)

`hubble_network` claims an advertisement when service data is present under
`FCA6` and non-empty. A bare `FCA6` in the service-UUID list with no service
data is presence only and is deliberately **not** claimed. It reports:

| Field | Source |
|-------|--------|
| `vendor` | `Hubble Network` |
| `service_uuid` | `fca6` |
| `protocol_version` | `byte0 >> 2` |
| `protocol` | `aes_ctr` / `unencrypted` / `aes_eax` / `unknown` |
| `sequence_number` | v0: `BE16(bytes 0–1) & 0x3FF` |
| `eid_hex` | v0: bytes 2–5; v2: bytes 3–10 — tagged as a **rotating** identifier |
| `auth_tag_hex` | v0: bytes 6–9; v2: last 4 — rotating |
| `ciphertext_hex`, `ciphertext_length` | the opaque body |
| `network_id`, `network_id_hex`, `customer_payload_hex` | v1 only |
| `nonce_salt_hex` | v2 only |
| `decode` | `header_only` (v0/v2), `plaintext` (v1), `truncated` (shorter than the version's header), `unrecognized_version` |
| `payload_hex` | the raw service data |

Identity: no field in the frame is stable — the EID rotates, the sequence
number counts, the address is random — so the parser keys identity off the
BLE address (one identity per address lifetime) and sets no stable key.
Device class `tracker` (the network's role, not a product claim).

## What We Cannot Parse

- The customer payload: AES under a device key provisioned by Hubble and
  never advertised. `pyhubblenetwork` needs the key (`hubble ble scan
  --key …`) to decrypt.
- Which device or vendor is on the other end — the SDK is generic; Hubble's
  cloud maps EID → device.
- A cross-rotation identity. The EID period is a firmware choice
  (`hubble_ble_advertise_expiration_get()`), 180 s in the reference sample.

## Detection Significance

- **A crowd-relayed IoT beacon.** Any phone running the Hubble Gateway SDK
  forwards these frames (with the phone's location) to Hubble's cloud — the
  same privacy model as AirTag/Tile networks, applied to third-party IoT.
- **Not a consumer product by itself.** Hubble sells the network; the device
  could be a logistics tracker, an agricultural sensor, or an OEM module
  inside something else.
- **Sequence number and EID** let a single capture session tell frames from
  one unit apart (consecutive `seq`, one EID) without any stable identifier
  leaking across rotations.

## References

- [`hubble-device-sdk` — `include/hubble/ble.h`](https://github.com/HubbleNetwork/hubble-device-sdk/blob/main/include/hubble/ble.h) — `HUBBLE_BLE_UUID 0xFCA6`, `HUBBLE_BLE_MAX_DATA_LEN 13`, `HUBBLE_BLE_ADV_HEADER_SIZE 12`, advertising-element layout, EID rotation
- [`hubble-device-sdk` — TI `hubble_ble_adv.c`](https://github.com/HubbleNetwork/hubble-device-sdk/blob/main/samples/freertos/ti/ble-beacon/src/hubble_ble_adv.c) — the `03 03 a6 fc | len 16 …` advertising header and the 180 s update period
- [`pyhubblenetwork` — `src/hubblenetwork/ble.py`](https://github.com/HubbleNetwork/pyhubblenetwork/blob/main/src/hubblenetwork/ble.py) — `_make_packet`: version nibble, AES-CTR / plaintext / AES-EAX layouts
- [`pyhubblenetwork` — `src/hubblenetwork/packets.py`](https://github.com/HubbleNetwork/pyhubblenetwork/blob/main/src/hubblenetwork/packets.py) — `SEQ_NO_MASK 0x3FF`, packet dataclasses
- [`gateway-sdk-python` — `scanner.py`](https://github.com/HubbleNetwork/gateway-sdk-python/blob/main/src/hubble_gateway/scanner.py) — the gateway filters on `FCA6` (and Tile `FEED`) and forwards `serviceData` + location
- [Bluetooth SIG member service UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFCA6` = Hubble Network Inc.
