# IoTV Nordic-UART IoT Device Family

## Overview

A fleet of BLE devices advertising `IoTV{6 hex chars}` local names,
backed by the standard Nordic UART Service (NUS) when actively
broadcasting. **14 distinct devices were captured in a single 2026
adwatch export session**, suggesting either a small commercial product
line or a custom in-house deployment that uses an off-the-shelf Nordic
SDK BLE example as its base.

The "IoTV" prefix is a working name — no public vendor attribution has
been confirmed. Candidates include: an IoT-visualization platform, a
training-class set of nRF dev boards, or a small commercial product
line. The pattern is distinctive enough that adwatch can attribute it
even without resolving the vendor.

## Identification

```
local_name:    "IoTV<6-hex>"      e.g. IoTV086405, IoTV976E1C
service_uuids: [180A, 180F, E001, 6E400001-…NUS…]   when active
               (empty)                              when idle / sleeping
```

| Service UUID | Role |
|--------------|------|
| `0x180A` | Standard Device Information service |
| `0x180F` | Standard Battery service |
| `0xE001` | Vendor-private 16-bit UUID (purpose unknown) |
| `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` | Nordic UART Service (NUS) — bidirectional serial-over-BLE |

The presence of NUS strongly implies a Nordic nRF5x / nRF52840 / nRF52833
chip running close to a stock SDK example. NUS is what `nrfutil`
itself uses for DFU and many open-source firmwares ship it as their
debug / control interface.

The parser matches on the local-name regex `^IoTV([0-9A-Fa-f]{6})$` so
both the idle (name-only) and active (name + UUIDs) broadcasts are
attributed. The metadata records which services were present, so
downstream consumers can tell active devices apart from sleeping ones.

## Device ID

The 6 hex characters at the tail of the name look like the last three
bytes of the hardware BLE address (matches the standard Nordic SDK
default `BLE_GAP_DEVNAME` pattern). It is stable across BLE-MAC
rotation and serves as adwatch's identity key:

```
identifier_hash = SHA256("iotv:{device_id}")[:16]
```

## Captured Device IDs (2026 export)

```
086405  308E53  74BACE  8EB410  962844  976E1C  AB393E
A08B91  BACA23  BFB24B  648268  C07547  C9462C  E86098
```

14 distinct devices. RSSI on every capture is between −90 and −99 dBm,
so they are at the edge of range — consistent with a single
neighbouring building or a fleet of devices in adjacent units.

## What We Cannot Parse Without GATT

- Device identification strings from the Device Information service
  (manufacturer name, model number, firmware version)
- Battery level
- Anything sent over the NUS RX/TX characteristics (the actual purpose
  of this fleet)

A passive scanner can only count and group them.

## Open Questions

- **Who is the vendor?** "IoTV" + a 6-hex serial does not match any
  public BLE product catalogue searched to date. If anyone recognizes
  this signature, please open an issue with a SKU pointer.
- Is the `0xE001` 16-bit UUID a vendor-specific service or a known
  but rarely-used assigned number we're missing? It is not in the
  Bluetooth-SIG 16-bit UUID registry at last check.
