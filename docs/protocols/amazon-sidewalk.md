# Amazon FE15 Proximity Beacon Plugin

## Overview

The Bluetooth SIG 16-bit service UUID `0xFE15` is allocated to **Amazon.com Services, Inc.** Devices advertising under FE15 emit a 16-byte privacy-preserving service-data payload with **no manufacturer data** and **no local name**. The payload is conservative on the wire: a fixed two-byte header followed by a 14-byte opaque blob that changes per re-emission of the same logical device (and the MAC rotates too).

We surface this beacon under the generic `beacon_type = amazon_fe15` and `device_class = amazon_proximity`. The most likely real-world identity is **Amazon Sidewalk** gateway neighbor-discovery — but Amazon's public Sidewalk specification does not publish the byte-level beacon format in a form we can quote, so this plugin does *not* claim Sidewalk identity in the parsed result. See *Vendor attribution* below.

## BLE Advertisement Format

### Identification

| Signal | Value |
|---|---|
| Service UUID (16-bit) | `FE15` (SIG → Amazon.com Services, Inc.) |
| Manufacturer data | absent |
| Local name | absent |
| Service data payload | exactly 16 bytes, prefix `00 02`, followed by a 14-byte opaque/encrypted blob |

We require **all four** signals — FE15 service-data slot present, 16-byte length, `0x00` `0x02` prefix — to match. Smaller / different prefixes are deliberately ignored so we don't over-claim a structure we have no evidence for.

### Payload Layout

```
+-------+-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
|  ver  | type  |               14-byte opaque proximity blob                          |
| 0x00  | 0x02  |                                                                      |
+-------+-------+----+----+----+----+----+----+----+----+----+----+----+----+----+----+
   0       1     2    3    4    5    6    7    8    9   10   11   12   13   14   15
```

- **`frame_version` (byte 0)** — fixed `0x00` across every observed emitter.
- **`frame_type` (byte 1)** — fixed `0x02` across every observed emitter. Other frame-type values almost certainly exist (Amazon defines several beacon types) but we have not captured them, so we don't speculate.
- **`proximity_blob_hex` (bytes 2..15)** — 14 bytes of high-entropy data. Likely an authenticated proximity token: an encrypted ID + truncated MIC. The blob differs between emitters and across re-emissions of the same device, which is consistent with a privacy-preserving short-rotation scheme.

### Privacy & Stable Identifiers

The blob is **privacy-rotated** and the BLE MAC is **random** (Apple's CoreBluetooth surfaces an opaque UUID, not the real MAC). A `stableKey` derived from either would be wrong — the same physical device will appear as a stream of unrelated identities. The parser therefore returns `stableKey: nil` and the `identifierHash` is derived from the per-scan MAC only (best-effort within a single sighting).

## Vendor Attribution

FE15 is firmly Amazon (SIG-assigned). The strongest candidate identity is **Amazon Sidewalk** — specifically the BLE-channel neighbor-discovery beacon emitted by Sidewalk gateways (Echo, Ring, etc.) to advertise authenticated proximity to nearby endpoints. Supporting circumstantial evidence:

- Sidewalk gateways are Echo / Ring smart-home hubs, which are highly prevalent in residential neighborhoods.
- Sidewalk beacons advertise an authenticated proximity blob; the `0x00 0x02 || <14-byte tail>` shape matches a typical short-token + MIC layout.
- 11 distinct emitters in a residential-area capture matches Sidewalk gateway density expectations.

But we cannot conclusively confirm Sidewalk from public docs: the Amazon Sidewalk Specification 1.0 references the Beacon-frame format in section 5, but does not publicly publish the SIG service-UUID it uses or the byte-level beacon layout in a form we can quote. Other plausible Amazon identities for FE15 include:

- **Echo Show / Echo Hub** local-device discovery
- **Tap-to-Alexa** pairing beacon
- Some other **Lab126** proximity service

To stay conservative we name the parser `amazon_fe15` and class it `amazon_proximity`. If a future capture or external spec confirms Sidewalk we will tighten the labels.

## Examples

| Capture (FE15 service-data hex) | Parsed |
|---|---|
| `0002afd81f1c09a49bc5ce308a2ea877` | `frame_version=0x00`, `frame_type=0x02`, `proximity_blob_hex=afd81f1c09a49bc5ce308a2ea877` |
| `00027d9165428515ace057e4db6815ff` | `frame_version=0x00`, `frame_type=0x02`, `proximity_blob_hex=7d9165428515ace057e4db6815ff` |
| `0002beee22140f6aee5454542e40d340` | `frame_version=0x00`, `frame_type=0x02`, `proximity_blob_hex=beee22140f6aee5454542e40d340` |
| `0002e3c41b5dc6b42acc14c0da94a613` | `frame_version=0x00`, `frame_type=0x02`, `proximity_blob_hex=e3c41b5dc6b42acc14c0da94a613` |

## Disjointness From Sibling Amazon Parsers

| Parser | Match key |
|---|---|
| `AmazonEchoParser` | FE00 service-data + `localName` starts with `"Echo "` |
| `AmazonFireTVParser` | FE00 service-data, 17-byte payload |
| `AmazonHIDRemoteParser` | manufacturer CID `0x0171` + HID-over-GATT service `0x1812` |
| `AmazonFE15Parser` | FE15 service-data, 16-byte `0x00 0x02 || ...` |

No two of these parsers overlap on the same wire signature.

## References

- Bluetooth SIG 16-bit UUID allocation list (`0xFE15` → Amazon.com Services, Inc.) — see the [SIG Assigned Numbers document](https://www.bluetooth.com/specifications/assigned-numbers/) and the mirrored [`blatann` reference index](https://blatann.readthedocs.io/en/latest/blatann.bt_sig.uuids.html).
- [Amazon Sidewalk Documentation home](https://docs.sidewalk.amazon/)
- [Amazon Sidewalk Specifications — Protocol Stack 1.0](https://docs.sidewalk.amazon/specifications/)
- [Amazon Sidewalk Gateways overview](https://docs.sidewalk.amazon/introduction/sidewalk-gateways.html)
- [Amazon Sidewalk Privacy and Security Whitepaper](https://www.amazon.com/gp/help/customer/display.html?nodeId=GRGWE27XHZPRPBGX)
