# ResMed CPAP/Sleep Devices -- BLE Protocol Notes

## Identification

- **Local Name Pattern**: `ResMed XXXXXX` (6-digit serial/device number)
- **Service UUID**: `0xFD56` (16-bit, registered to **ResMed Ltd** by the Bluetooth SIG)
- **Manufacturer Data**: `8d 03 00` (3 bytes observed)
- **BLE Company ID**: `0x038D` (ResMed Ltd)
- **MAC OUI**: `00:23:6D` (ResMed Ltd)
- **Address Type**: Random (BLE privacy enabled)

## Overview

ResMed is an Australian medical device company that manufactures CPAP (Continuous
Positive Airway Pressure) and BiPAP machines for treating sleep apnea. Their
current product lines include the AirSense 10, AirSense 11, AirCurve 10/11,
and AirMini travel CPAP.

Starting with the AirSense 11 (released 2021), ResMed devices include built-in
Bluetooth Low Energy for communication with the **myAir** companion app
(iOS/Android). The AirSense 10 does not have native BLE -- only cellular and
SD card data paths -- though some later AirSense 10 models or accessories may
advertise over BLE.

The BLE connection is used for:
- Initial device setup and pairing (QR code or 4-digit KEY code)
- Real-time therapy control (pressure trials, comfort settings)
- Firmware updates (over-the-air via BLE + WiFi/cellular)
- Session data sync to the myAir cloud platform

**Note**: The primary therapy data path is cellular (to ResMed's cloud), not
BLE. The myAir app retrieves data from ResMed's servers, not directly from the
device over Bluetooth. BLE is used for local device control and setup.

## Advertisement Structure

### Service UUID (AD Type 0x03 / 0x07)

The device advertises the 16-bit service UUID `0xFD56`. This UUID is officially
registered to **ResMed Ltd** in the Bluetooth SIG's 16-bit UUID for Members
registry. UUIDs in the `0xFD00`-`0xFDFF` range are reserved for member companies.

Full 128-bit form: `0000FD56-0000-1000-8000-00805F9B34FB`

### Manufacturer Specific Data (AD Type 0xFF)

Observed payload: `8d 03 00` (3 bytes)

Breakdown:
- Bytes 0-1: `8d 03` -- BLE Company ID `0x038D` (little-endian) = **ResMed Ltd**
- Byte 2: `0x00` -- Payload (1 byte)

The single payload byte `0x00` likely represents a minimal status/flags field.
With only 1 byte of actual manufacturer data beyond the company ID, this
advertisement is primarily a presence beacon rather than carrying rich telemetry.
Possible interpretations of the payload byte:
- Device state flags (e.g., pairing mode, therapy active/idle)
- Protocol version indicator
- Always zero in passive advertising (richer data exchanged post-connection)

The consistency of `0x00` across multiple devices and long observation periods
suggests this is either a static value or a "not in active session" indicator.

### Local Name

Format: `ResMed XXXXXX` where XXXXXX is a 6-digit number. This appears to be
the device's serial number or a derivative of it. ResMed devices have both a
serial number (longer, on the device label) and a 3-digit "Device Number" (DN)
used for myAir registration. The 6-digit number in the BLE local name may be
the last 6 digits of the full serial number.

### Address Type

Random address (BLE privacy). The device uses a random (likely static random)
BLE address rather than its public IEEE MAC address. This is standard practice
for medical devices to limit tracking.

## Known Protocol Details

### Security Model

ResMed employs multiple layers of BLE security:
- **Pairing**: Requires scanning a QR code on the device or manually entering a
  4-digit KEY code. This prevents unauthorized pairing.
- **Bluetooth-level encryption**: Standard BLE pairing with bonding.
- **Application-level encryption**: Additional encryption layer on top of BLE
  for therapy data transmission.
- **Unique keys per device**: Each device has unique pairing credentials.

### GATT Services (Inferred)

No public documentation of ResMed's GATT service table exists. Based on the
device's functionality, expected services include:

| Service | Purpose | Notes |
|---------|---------|-------|
| `0xFD56` (ResMed) | Primary service | Custom ResMed protocol |
| Generic Access (`0x1800`) | Standard BLE | Device name, appearance |
| Generic Attribute (`0x1801`) | Standard BLE | Service changed |
| Device Information (`0x180A`) | Standard BLE | Model, serial, firmware |
| Battery Service (`0x180F`) | Possible | If battery-backed |

The `0xFD56` service likely contains custom characteristics for:
- Therapy session data (AHI, leak rate, pressure, usage hours)
- Device settings (pressure, ramp, humidifier, EPR)
- Firmware update control
- Device status and error codes

### Data Format

ResMed therapy data typically includes:
- **AHI** (Apnea-Hypopnea Index): events per hour
- **Mask leak rate**: L/min
- **Pressure**: cmH2O (set pressure, actual pressure, 95th percentile)
- **Usage hours**: total and per-session
- **Events**: obstructive apneas, central apneas, hypopneas, RERA
- **EPR** (Expiratory Pressure Relief) settings
- **Humidifier** settings and status

The SD card file format is well-documented by the OSCAR project (see below),
but the BLE transfer format is proprietary and not publicly reversed.

## Open Source References

### OSCAR (Open Source CPAP Analysis Reporter)
- **Website**: https://www.sleepfiles.com/OSCAR/
- **GitHub**: https://github.com/operativeF/oscar (community fork)
- **What it does**: Reads ResMed SD card data files and produces detailed
  therapy analysis. Supports AirSense 10, AirSense 11, and other brands.
- **Relevance**: OSCAR understands ResMed's *file-based* data format (from the
  SD card), but does not interact with the BLE protocol. It provides the best
  reference for understanding what data types ResMed devices produce.
- **Note**: OSCAR reads data from SD cards, not via BLE. Some community members
  use WiFi-enabled SD cards (EZ Share) to get data wirelessly.

### Related Projects
- **ezshare_cpap** (https://github.com/iitggithub/ezshare_cpap): Script to
  pull CPAP data from AirSense 10/11 via EZ Share WiFi SD card
- **SleepApnea_WifiUploads_SleepHQ** (https://github.com/murraydavis/SleepApnea_WifiUploads_SleepHQ):
  Raspberry Pi setup for capturing data via WiFi SD card
- **Sleeper** (https://github.com/CascadePass/Sleeper): CPAP/BiPAP data
  visualizer

### Bluetooth SIG References
- **UUID 0xFD56**: Registered to ResMed Ltd in the Bluetooth SIG 16-bit UUID
  for Members registry
  (https://www.bluetooth.com/specifications/assigned-numbers/)
- **Company ID 0x038D**: ResMed Ltd in the Bluetooth SIG Company Identifiers
  registry
- **Nordic Semiconductor Bluetooth Numbers Database**:
  https://github.com/NordicSemiconductor/bluetooth-numbers-database

### No Known BLE Protocol Reversing

As of this writing, there are no known public projects that have reverse-
engineered ResMed's BLE GATT protocol. ResMed's terms of service explicitly
prohibit reverse engineering. The BLE protocol appears to use application-level
encryption, making passive sniffing insufficient for protocol analysis.

The community has focused on SD card data extraction (OSCAR) and WiFi SD card
solutions rather than BLE protocol work.

## Observed in adwatch

From a passive BLE scan export:

| Field | Value |
|-------|-------|
| Local Name | `ResMed 111682`, `ResMed 828156` |
| Service UUID | `FD56` |
| Manufacturer Data | `8d0300` |
| Address Type | random |
| Sighting Count | 844 (over ~5 hours for one device) |
| RSSI Range | -72 to -100 dBm |
| Ad Interval | ~21 seconds average (844 sightings / 5 hours) |

### Observations

- **High advertisement rate**: ~21-second average interval is typical for BLE
  devices that want to be discoverable but are not in active connection. Medical
  devices often use moderate intervals to balance discoverability with power
  consumption (though CPAP machines are mains-powered, so battery is not a
  concern).
- **Consistent manufacturer data**: The `8d0300` payload was identical across
  multiple devices and over the full observation period, confirming this is a
  static advertisement rather than rotating telemetry.
- **Random addresses**: Both observed devices used random BLE addresses,
  consistent with ResMed's privacy-conscious approach.
- **Multiple devices**: Two distinct ResMed devices were observed in the same
  scan area, likely in a household with multiple CPAP users or a
  clinical/retail setting.
- **Moderate RSSI**: The -72 to -100 dBm range suggests the devices were in an
  adjacent room or moderate distance (5-15 meters typical for this range).

### Parser Potential

A basic identification-only parser is straightforward:
- Match on local name pattern `ResMed \d{6}` or service UUID `FD56`
- Extract serial/device number from local name
- Decode company ID from manufacturer data (confirm `0x038D`)
- No rich telemetry available from passive scanning alone

The advertisement carries minimal data beyond device identification. Useful
parsed fields would be:
- `device_number`: The 6-digit number from the local name
- `company_id`: `0x038D` (ResMed Ltd)
- `device_type`: "CPAP/Sleep Therapy Device"
