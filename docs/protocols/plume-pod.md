# Plume Design / OpenSync Wi-Fi Pod — BLE Onboarding Beacon

## Overview

Plume Design Inc makes the SuperPod / PowerPod Wi-Fi mesh pods sold directly
(HomePass) and, through its OpenSync firmware stack, the ISP-branded pods
many carriers ship (Comcast xFi Pods, Bell Wi-Fi Pods, Charter/Spectrum and
others list OpenSync-certified pods). Every OpenSync node runs a Bluetooth
Manager (BLEM) that advertises a small **onboarding beacon** so the mobile
app can find a new pod, read its serial and connectivity state, and pair
with it to push Wi-Fi credentials. The beacon layout is published in the
OpenSync source tree, so this parser decodes a vendor-documented frame
rather than an inferred one.

First captured in the 2026-08-25 telemetry sweep: two units, one sighting
each, four minutes apart, random addresses, no local name.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Company ID | `0x0A17` | Bluetooth SIG: **Plume Design Inc** |
| Service UUID | `0xFE71` | Bluetooth SIG member UUID: **Plume Design Inc** — advertised on every captured frame; reported by the parser, not required |
| Manufacturer payload | exactly 20 bytes, first byte `0x05` | `ble_adv_data_general_t` in OpenSync `src/blem/src/ble_adv_data.h` |
| Local name | none (advertising PDU) | OpenSync can put a Complete Local Name in the scan response; not seen in passive capture |

Two independent SIG registrations (CID and member UUID) agree on the
vendor, and the firmware's own header file defines the payload — this is a
HIGH-confidence attribution.

### Manufacturer Data Layout

Bytes after the 2-byte little-endian company ID (`17 0a` on the wire):

| Offset | Field | Size | OpenSync definition |
|--------|-------|------|---------------------|
| 0 | `version` | 1 | "Version of this beacon data structure, fixed value 0x05" |
| 1–12 | `serial_num` | 12 | "ASCII-encoded node serial number, no null-termination required if 12-char long" — NUL-padded when shorter (a 10-character serial was observed) |
| 13 | `msg_type` | 1 | "Type of the payload currently present in the `msg` field" — `0x00` in both captures |
| 14 | `msg.status` | 1 | Connectivity status bitfield (valid when `msg_type` is `0x00`) |
| 15 | `msg._rfu` | 1 | Unused |
| 16–19 | `msg.pairing_token` | 4 | "Random token used in pairing passkey generation" |

The advertising data element itself is `len = 1 + 2 + 20 = 23`, type
`0xFF`; the flags element is prepended by the stack.

### Connectivity status bitfield (`msg_type` 0x00)

From OpenSync `src/blem/src/blem_connectivity_status.h`
(`ble_connectivity_status_bit_t`):

| Bit | Mask | Meaning | Parser flag |
|-----|------|---------|-------------|
| 0 | `0x01` | Ethernet physical link | `eth_phy_link` |
| 1 | `0x02` | Wi-Fi physical link | `wifi_phy_link` |
| 2 | `0x04` | Backhaul over Ethernet | `backhaul_over_eth` |
| 3 | `0x08` | Backhaul over Wi-Fi | `backhaul_over_wifi` |
| 4 | `0x10` | Connected to router | `connected_to_router` |
| 5 | `0x20` | Connected to Internet | `connected_to_internet` |
| 6 | `0x40` | Connected to cloud | `connected_to_cloud` |
| 7 | `0x80` | Unknown / initial state | `unknown` |

Observed values: `0x01` (Ethernet link only — a pod that has a cable but no
backhaul yet) and `0x15` (Ethernet link + Ethernet backhaul + connected to
router, but not to the Internet or cloud). Both are ordinary onboarding /
outage states, which is exactly when the beacon is meant to be useful.

### Example (real bytes, synthetic serial digits)

```
17 0a | 05 | 4a 50 47 35 30 30 30 30 30 30 30 30 | 00 | 01 | 00 | d2 18 41 56
CID    ver  "JPG500000000"                        msg  st   rfu  pairing_token
```

```
17 0a | 05 | 34 41 38 43 30 30 30 30 30 30 00 00 | 00 | 15 | 00 | 00 00 00 00
CID    ver  "4A8C000000" + 2 x NUL                msg  st   rfu  pairing_token
```

The two real captures carried a 12-character serial (three letters + nine
digits) and a 10-character serial (four alphanumerics + six digits). The
serial is what an owner types (or scans) to claim the pod in the HomePass /
ISP app, so the real digits are not reproduced here or in the app's test
fixtures — the byte shapes above are the real frames with the digits
replaced.

## Parser Scope (passive-only)

The parser accepts a frame when CID `0x0A17` is present, the manufacturer
payload is exactly 20 bytes, byte 0 is `0x05`, and the serial field holds
at least one alphanumeric ASCII byte followed only by NUL padding. It
reports:

| Field | Source |
|-------|--------|
| `vendor` | `Plume Design Inc` |
| `company_id` | `0x0A17` |
| `service_uuid` | `FE71` when advertised (absent otherwise) |
| `beacon_version` | byte 0, `0x05` |
| `serial` | bytes 1–12, NUL padding stripped |
| `msg_type` | byte 13 |
| `status_hex`, `status_flags`, `connected_to_internet`, `connected_to_cloud`, `rfu_hex`, `pairing_token_hex` | decoded from `msg` when `msg_type` is `0x00` |
| `msg_hex` | the raw six `msg` bytes for any other `msg_type` |

Any other `0x0A17` frame (different version byte, different length, an
empty or non-alphanumeric serial field) is left unclaimed rather than
guessed.

Identity is keyed on the serial (`plume_pod:<serial>`), which survives
BLE address rotation; the pairing token is tagged as a rotating identifier.
Device class `wifi_access_point`.

## What We Cannot Parse

- Which pod model (SuperPod, PowerPod, an ISP-branded OpenSync pod) — the
  beacon carries no product code; the serial prefix may encode it but that
  mapping is not published.
- Wi-Fi credentials, pairing passkeys, or anything exchanged after the
  central connects — the token is only one input to passkey generation.
- The `msg` layout for any `msg_type` other than `0x00`; the OpenSync
  header documents only the connectivity-status message.

## Detection Significance

- **Home / small-office Wi-Fi mesh.** A pod beacon pinpoints an OpenSync
  installation (Plume HomePass or an ISP mesh product).
- **Onboarding or outage in progress.** Pods advertise this beacon while
  they are not fully online; the status bits say whether the pod has a
  cable, a backhaul, a router, Internet or cloud.
- **Stable serial.** The node serial persists across MAC rotation and
  reboots, so a pod is re-identifiable across captures.

## References

- [OpenSync `ble_adv_data.h`](https://github.com/plume-design/opensync/blob/master/src/blem/src/ble_adv_data.h) — `ble_adv_data_general_t`, the beacon layout (version, `serial_num[12]`, `msg_type`, `msg`)
- [OpenSync `blem_connectivity_status.h`](https://github.com/plume-design/opensync/blob/master/src/blem/src/blem_connectivity_status.h) — `ble_connectivity_status_bit_t`, the status bitfield
- [OpenSync Wiki — Bluetooth Manager (BLEM)](https://opensync.atlassian.net/wiki/spaces/OCC/pages/40054194179/Bluetooth+Manager+BLEM) — `AW_Bluetooth_Config` and the advertising modes
- [Bluetooth SIG company identifiers](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml) — `0x0A17` = Plume Design Inc
- [Bluetooth SIG member service UUIDs](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml) — `0xFE71` = Plume Design Inc
