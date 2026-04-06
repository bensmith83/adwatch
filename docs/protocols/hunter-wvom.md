# Hunter WVOM (Wireless Valve Output Module) -- BLE Protocol Notes

## Identification

- **Local Name Pattern**: `WVOM-XXXXXX` (6-digit serial number, e.g., `WVOM-147516`)
- **Service UUID**: `0ED3E3D3-8CD8-4F29-8FEC-A7D3A2C5443E` (128-bit custom UUID)
- **Manufacturer Data**: None observed in advertisements
- **Address Type**: Random (BLE privacy enabled)
- **FCC ID**: `M3U-WVOM`

## Overview

The WVOM (Wireless Valve Output Module) is manufactured by **Hunter Industries**
(San Marcos, CA), a major irrigation equipment company. It is a plug-in module
for Hunter ICC2 and HCC irrigation controllers that enables wireless control of
sprinkler valves via LoRa radio, eliminating the need for copper field wiring to
valve boxes.

The WVOM serves as a bridge between two wireless technologies:
- **Bluetooth Low Energy (BLE)**: Used for smartphone-to-WVOM communication via
  the **Hunter WVL App** (iOS/Android). Range is approximately 50 ft (15 m)
  line-of-sight. Used for programming, diagnostics, and firmware updates.
- **LoRa Radio**: Used for WVOM-to-WVL (Wireless Valve Link) field communication
  over distances up to 2,000 ft (650 m). Controls DC latching solenoid valves
  (Hunter PN-458200) in the field.

The WVOM has no built-in controls -- only status LEDs. All configuration is done
through the BLE-connected WVL App. The system supports up to 54 wireless stations
per controller.

**Product Line**:
- WVOM -- US market version
- WVOM-E -- International/EU market version (complies with Directive 2014/53/EU)
- WVL-100 / WVL-200 / WVL-400 -- Field-side wireless valve links (1/2/4 station)

## Advertisement Structure

The WVOM advertises with two distinct BLE advertisement variants:

### Variant 1 -- Service Advertisement (Primary)
- **Local Name**: `WVOM-XXXXXX` (6-digit serial number)
- **Service UUID**: `0ED3E3D3-8CD8-4F29-8FEC-A7D3A2C5443E`
- **Manufacturer Data**: None
- **Purpose**: Likely the connectable advertisement used by the WVL App to
  discover and identify WVOM modules. The serial number in the local name
  matches how the WVL App displays available devices in its scan list.

### Variant 2 -- Minimal Advertisement
- **Local Name**: Not present or empty
- **Service UUID**: None
- **Manufacturer Data**: None
- **Purpose**: Possibly a scan response packet, a non-connectable beacon for
  presence detection, or a LoRa-related BLE side-channel. Observed less
  frequently (~16% of total sightings).

Both variants share the same BLE device address (random type).

## Known Protocol Details

### BLE Communication
- The 128-bit service UUID `0ED3E3D3-8CD8-4F29-8FEC-A7D3A2C5443E` is a custom
  UUID defined by Hunter Industries -- it is not registered with the Bluetooth SIG.
- The WVL App uses this UUID to discover WVOM modules during scanning.
- Once connected, the app provides: station programming, diagnostics, firmware
  updates, and LoRa link quality monitoring.
- No GATT characteristic UUIDs have been publicly documented.

### LoRa Communication
- The LoRa radio operates on license-free ISM bands.
- Field communication is one-way (WVOM to WVL) for valve actuation, with
  bidirectional status reporting.
- LoRa protocol details are proprietary to Hunter Industries.

### Authentication / Security
- No pairing or PIN entry has been documented for BLE connections in the
  available manuals. The WVL App appears to connect directly to any WVOM
  within range.
- The random BLE address type suggests MAC address rotation is in use,
  though the address was stable across the observed 5-hour window.

## Open Source References

No open-source reverse engineering efforts, Home Assistant integrations, or
protocol documentation for the Hunter WVOM BLE protocol were found as of
April 2025. The BLE protocol remains undocumented outside of Hunter's
proprietary WVL App.

Potentially relevant resources:
- [FCC Filing M3U-WVOM](https://fcc.report/FCC-ID/M3U-WVOM) -- FCC test
  reports and installation manual
- [Hunter WVL Support Page](https://www.hunterirrigation.com/support/wvl-wireless-valve-output-module)
  -- official documentation, firmware updates, compliance info
- [Hunter WVOM Owner's Manual (PDF)](https://www.hunterirrigation.com/sites/default/files/2024-08/RC-184-OM-WVOM-EN-web.pdf)
- [Hunter WVL Written Specifications (PDF)](https://www.hunterirrigation.com/sites/default/files/2024-10/RC-184-WVL-Written-Specifications-REV-102424.pdf)
- [ESPEasy Issue #5158](https://github.com/letscontrolit/ESPEasy/issues/5158) --
  request to add Hunter BTT (BLE) as an ESPEasy plugin (related Hunter BLE product)

## Observed in adwatch

| Field               | Value                                          |
|---------------------|------------------------------------------------|
| Local Name          | `WVOM-147516`                                  |
| Service UUID        | `0ED3E3D3-8CD8-4F29-8FEC-A7D3A2C5443E`        |
| Device Address      | `8898969B-28F0-0759-AFA2-D7F752A61E0E`         |
| Address Type        | Random                                         |
| RSSI Range          | -75 to -101 dBm (moderate to far)              |
| Observation Window  | ~5 hours                                       |
| Variant 1 Sightings | 172 (with service UUID and local name)         |
| Variant 2 Sightings | 32 (no service data or UUIDs)                  |
| Manufacturer Data   | None in either variant                         |

The RSSI range of -75 to -101 suggests the WVOM was mounted at a moderate
distance from the scanner, consistent with an irrigation controller installed
outdoors or in a garage/utility area. The device advertised continuously over
the full observation window, which is expected since the WVOM is AC-powered
via the irrigation controller.

## Plugin Feasibility

A basic adwatch plugin for the WVOM would be straightforward for identification
purposes using the local name pattern `WVOM-*` and/or the custom service UUID.
However, there is no known parseable data in the advertisements -- no
manufacturer data, no service data payloads, and no temperature/sensor readings
in the ads. The BLE advertisements appear to serve only as a discovery mechanism
for the WVL App.

A plugin could extract and display:
- Device serial number (from the local name suffix)
- Presence/availability status
- Signal strength trends

Deeper integration (reading valve status, station programming) would require
a GATT connection and reverse engineering the characteristic protocol, which
is currently undocumented.
