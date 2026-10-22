# ZH-SDK "Berry-Ring" White-Label Rings (Noise Luna and others)

## Overview

The **ZH white-label wearable SDK** (`com.zhapp.ble`, `ZH_SDK_20260920_V2.4.8`,
ring protocol "Berry-Ring" `BPC1.241120.001`) is behind the **Noise Luna Ring**
(`com.noisefit.luna`) and other budget "Berry-Ring" rings. Discovery is
**entirely by a service-data AD element under 16-bit UUID `0xFE78`**. The
payload is a fixed-offset cleartext record containing the device's **own MAC
address**, a device-type code, firmware version, capability/role bitfields and a
secondary ("headset") MAC.

No manufacturer data, no name filter (the SDK uses `setServiceUuid(null)` and
filters in software).

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Service data UUID | `0xFE78` (`0000fe78-0000-1000-8000-00805f9b34fb`) | `UuidUtils.SCAN_RECORD` (`UuidUtils.java:7`). See attribution note below. |
| Company ID | — | No manufacturer data |
| Local name | — | Read as-is, never matched |

> **Attribution contradiction.** The report says `0xFE78` is "publicly assigned
> to Huami/Zepp". adwatch's sources disagree: bleak's SIG table lists `0xFE78`
> as **Hewlett-Packard Company**, `src/adwatch/plugins/hp_printer.py` matches
> `fe78` as an HP printer UUID, and `src/adwatch/plugins/google_nearby_share.py`
> treats `fe78` service data as Bose. Either way `0xFE78` is not unique to this
> fleet — a parser must apply the byte-structure check below, and the existing
> HP/Bose plugins will also fire on Berry rings unless they get stricter.

### `0xFE78` service-data payload (offsets after the UUID, as adwatch receives it)

| Offset | Field | Size | Decode |
|--------|-------|------|--------|
| 0–5 | Device MAC | 6 | natural order `[0]:[1]:…:[5]` |
| 6–7 | deviceType | 2 | uint16 **LE**, rendered as a decimal string; `50000` (`50 C3`) = DFU sentinel |
| 8–10 | Firmware version | 3 | initially big-endian `v{b8}.{b9}.{b10}`; for BERRY / BERRY-RING re-read LE `v{b10}.{b9}.{b8}` |
| 11 | Capability bitfield #1 | 1 | table below |
| 12 | Capability bitfield #2 | 1 | table below |
| 13 | (unused) | 1 | not read |
| 14–19 | Secondary "headsetMac" | 6 | forward order (APRICOT/default); for BERRY read from **15–20 reversed**. Often zero/unused on a standalone ring. |

**DFU state:** an 8-byte payload whose deviceType = `50000` means the device is
mid-firmware-update; parsing stops there.

Bitfield #1 (byte 11): `0x80` isBind, `0x40` isUserMode (**true when bit is 0**),
`0x20` hasBindingFunction, `0x10` isSupportHeadset, `0x08` isHeadsetBond, `0x04`
isHeadsetBroadcast, `0x02` isDfu, `0x01` protocol selector (`0` APRICOT, `1`
BERRY).

Bitfield #2 (byte 12): `0x80` isDualConnection, `0x40` isNewPhoneMode, `0x20`
**BERRY-RING selector**.

**Positive Berry-Ring ID:** `0xFE78` payload > 12 bytes with byte 11 `& 0x01`
and byte 12 `& 0x20` both set.

## What We Can Parse from Advertisements

Embedded MAC, deviceType, firmware version, bind / user-mode / dual-connection /
new-phone-mode flags, DFU state, protocol family (APRICOT/BERRY/BERRY-RING),
secondary MAC.

## What Requires GATT

HR / SpO2 / sleep — over the `0x6666` protobuf GATT service (`0x0050`/`0x005e`
notify, `0x005f` write), plaintext per the report.

## Identity Hashing

Use the embedded MAC (bytes 0–5): `SHA256("zh-berry:{embedded_mac}")[:16]`. It
survives link-layer address rotation (HIGH confidence per the report — proven by
the SDK's cached-hex constructor reading these bytes as the device address).

## Detection Significance

- **MAC-in-payload defeats address randomization** — a permanent per-device
  identifier for any passive observer.
- deviceType + firmware give a stable model/firmware fingerprint.
- Bind / new-phone / DFU bits leak provisioning lifecycle events.

## adwatch Status

No plugin decodes this. `hp_printer.py` (service UUID `fe78`) and
`google_nearby_share.py` (Bose `fe78` service data) may currently mis-attribute
Berry rings. A future plugin should match `0xFE78` service data with the
structure gate above and decode the table.

## References

- apk-ble-hunting `reports/noisefit-luna_passive.md` (and `reports/noisefit-luna.md`)
- Code cited by the report: `com.zhapp.ble.bean.ScanDeviceBean`
  (`parsingRecord` `:212-318`, cached-hex ctor `:88-210`, MAC `:130-146`),
  `UuidUtils.java:7`, `BleUtils.java:23-30` (bit order),
  `NordicsemiBleScanner.java:136`
