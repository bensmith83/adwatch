# PowerDrive DC-AC Vehicle / Marine Power Inverter

## Overview

PowerDrive (a.k.a. "PowerDrive Plus") is a U.S. accessory brand distributed
through Sound of Tristate, Lowe's, A1 Truck Parts, and Overton's. Their
**PD-series** is a line of 12V DC to 120V AC power inverters intended for
trucks, RVs, boats, work vans, and jobsite trailers. Capacity tiers run
from 1000W to 3000W (PD1000 / PD1500 / PD2000 / PD3000); higher tiers add
extra NEMA outlets, more USB ports, and a wired remote. Bluetooth control
is the differentiating feature versus the bare-bones competition: a phone
app reports input voltage, output load, temperature, and fault state, and
toggles the inverter on/off remotely.

Captured in `research/nearsight_export.json` (one distinct device, seven
sightings):

```
localName    = "POWERDRIVER-L2FBA"
serviceUUIDs = []
mdata        = (absent)
addressType  = random
RSSI         = -83 to -95
```

All operational telemetry lives behind a GATT connection. The advertisement
only carries the device name; nothing in it identifies the specific wattage
tier.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `POWERDRIVER-<5-alphanumeric>` | e.g. `POWERDRIVER-L2FBA`. Five uppercase A-Z/0-9 characters, factory default. User may rename via the app, in which case the parser stops matching |
| Manufacturer data | (absent) | — |
| Service UUIDs | (absent in advertisement) | The vendor GATT service appears only after connect; not advertised |
| Service data | (absent) | — |
| Address type | `random` | Rotating private address |

The suffix `L2FBA` (and similar) is a per-unit device hash, almost certainly
the last 5 nibbles of the BLE MAC or a factory serial. It is stable for a
given physical inverter as long as the user has not renamed the device in
the app.

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Vendor | hard-coded | `PowerDrive` |
| Model family | hard-coded | `PD series` |
| Device class | hard-coded | `power_inverter` |
| Device suffix | localName | The 5-char tail after `POWERDRIVER-` |
| Device name | localName | Full advertised name |

### What We Cannot Parse from the Advertisement

- Specific model (PD1000 vs PD1500 vs PD2000 vs PD3000). The advertisement
  carries no wattage / SKU hint; all units share the `POWERDRIVER-` prefix.
- Input DC voltage, output AC load, output frequency, temperature.
- Fault codes (over-temp, low-battery, overload, short-circuit).
- On/off state of the AC outlets.
- Firmware version.

All of those live behind the vendor GATT service after connect.

## Stable Identity

The 5-character suffix in the local name is per-unit and survives MAC
rotation, so it makes a better stable key than the rotating private MAC:

```
stable_key = powerdrive_inverter:<suffix-lowercased>
```

If the local name is missing or malformed (corrupted ad, user-renamed
device), fall back to `powerdrive_inverter:mac:<mac>` — but note that this
fallback won't survive MAC rotation, so the same physical inverter will
appear as multiple devices.

## Detection Significance

- **Strong vehicular / off-grid context clue.** PowerDrive PD-series
  inverters are not consumer-home gear; they are sold through truck parts,
  RV, marine, and jobsite channels. A PowerDrive sighting is a strong
  indicator the surrounding scene is one of:
  - A work truck, service van, or pickup with a slide-in inverter
  - An RV, camper, or travel trailer running shore-power accessories off
    the house battery
  - A boat (especially fishing / cabin cruiser class) with a 12V house
    bank powering AC galley appliances
  - A jobsite trailer, food truck, or mobile-vendor cart
  - A construction site with a pickup parked nearby running power tools
- Co-located with other vehicle signatures (OBD2 dongles, dashcams,
  car-audio head units, TPMS sensors), the inference is unambiguous.
- A stationary PowerDrive sighted over multiple days at the same RSSI
  pattern suggests an RV park, marina slip, or fleet yard rather than
  a moving vehicle.
- High RSSI (greater than -70 dBm) means the inverter is within roughly
  10 m — close enough that the surrounding vehicle is the most likely
  host.

## References

- PowerDrive PD1500 product listing — <https://www.amazon.com/PowerDrive-PD1500-1500W-Bluetooth-Inverter/dp/B00VPYUVJ0>
- PowerDrive PD2000 product manual — <https://www.manualshelf.com/manual/powerdrive/pd2000/full-product-manual-english.html>
- PowerDrive PD3000 distributor page — <https://www.soundoftristate.com/powerdrive-pd1500>
- PowerDrive PD1000 manual — <https://www.manualslib.com/manual/2961617/Powerdrive-Pd1000.html>
- Capture: `research/nearsight_export.json`, one unit, seven sightings
