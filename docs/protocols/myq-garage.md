# Chamberlain / LiftMaster MyQ Garage Door Opener

## Overview

Chamberlain and LiftMaster MyQ garage door openers broadcast BLE advertisements for local device discovery and initial Wi-Fi commissioning by the MyQ mobile app. MyQ is Chamberlain Group's smart garage platform, encompassing devices sold under the Chamberlain, LiftMaster, Craftsman, and Raynor brands. MyQ-enabled garage door openers and smart garage hubs (e.g. MYQ-G0401) use Wi-Fi for cloud connectivity; BLE is used during setup and continues advertising afterward (purpose unconfirmed).

The BLE advertisement serves primarily as a **local discovery and commissioning beacon**. The MyQ app uses BLE to find nearby MyQ devices during initial setup, then transitions to Wi-Fi for ongoing cloud-based control. Note: MyQ's "auto-open on arrival" / Connected Garage features use **GPS geofencing through the cloud** (often via vehicle infotainment integrations such as Tesla, Nissan, INFINITI), not BLE proximity. The continuous BLE advertising observed post-commissioning therefore appears to be for re-discovery/re-pairing, not active proximity control.

Actual garage door control is handled through:
1. **Cloud API** (myQ API v6, OAuth-based) — primary control path
2. **Security+ 2.0** — encrypted rolling-code serial protocol over the wired bus between the motor unit and wall panel
3. **BLE GATT** — likely used only during commissioning to configure Wi-Fi credentials

The BLE advertisement itself does **not** expose door state, and passive observation reveals only device presence and identity.

## BLE Advertisement Format

### Identification

| Signal | Value | Notes |
|--------|-------|-------|
| Local name | `MyQ-XXX` pattern | 3-char alphanumeric suffix = last 3 chars of hub serial (e.g. `MyQ-017`, `MyQ-75D`, `MyQ-EF0`) |
| Service UUID | `26D91A37-C279-4D0F-96A1-532CE41CE0F6` | 128-bit custom UUID, not registered with Bluetooth SIG |
| Manufacturer data prefix | `7808` | Company ID `0x0878` (The Chamberlain Group, Inc.) |
| Company ID | `0x0878` (decimal 2168) | Registered to The Chamberlain Group, Inc. by Bluetooth SIG |

### Manufacturer Data

| Offset | Length | Field | Notes |
|--------|--------|-------|-------|
| 0-1 | 2 bytes | Company ID | `0x0878` — Chamberlain Group (little-endian: `7808`) |
| 2 | 1 byte | Unknown | `0x2B` or `0x2E` observed — possibly protocol version, firmware revision, model variant, or status flags. No public reverse-engineering documents the semantics. |
| 3 | 1 byte | Unknown | `0x00` observed consistently — likely padding or reserved. |

The manufacturer data payload is minimal (only 2 bytes after company ID). No publicly available reverse-engineering work (HomeAssistant `myq` integration, hjdhjd/myq, ratgdo, Konnected blaQ) documents the structure of these bytes — all of those projects target either the cloud HTTP API (hjdhjd/myq) or the wired Security+ 2.0 bus (ratgdo, blaQ), not the BLE advertisement. Treat the offset-2 byte as opaque until a sniffer-level study is published.

### Service UUID

The 128-bit UUID `26D91A37-C279-4D0F-96A1-532CE41CE0F6` is advertised as a complete/incomplete list of 128-bit service UUIDs. This is a **vendor-specific UUID** (not derived from the Bluetooth SIG base UUID), confirming it is a custom Chamberlain service. It likely corresponds to a proprietary GATT service used during BLE commissioning (Wi-Fi provisioning, device pairing).

### What We Can Parse from Advertisements

| Field | Source | Notes |
|-------|--------|-------|
| Device presence | local_name | MyQ garage door opener nearby |
| Device ID | local_name suffix | e.g. `75D` from `MyQ-75D` |
| Manufacturer | company_id `0x0878` | Chamberlain Group |

### What We Cannot Parse (requires GATT)

- Door state (open / closed / opening / closing)
- Firmware version
- Device model (wall mount, belt drive, etc.)
- Battery level (for battery backup models)
- Light status

## Local Name Pattern

```
MyQ-{device_id}
```

Examples: `MyQ-75D`, `MyQ-017`, `MyQ-EF0`

Per Chamberlain/LiftMaster setup documentation, the suffix is the **last three characters of the hub's serial number**. The same pattern is used as the SoftAP Wi-Fi SSID during fallback web-based provisioning (`setup.myqdevice.com`). MyQ serial numbers are alphanumeric (10–12 chars, mixed letters and digits), so the suffix may contain any alphanumeric characters — observed examples happen to be hex-compatible but the parser should not assume hex validity.

## Device Class

```
garage_door
```

## Identity Hashing

```
identifier = SHA256("{mac}:{local_name}")[:16]
```

## Known Protocol Details

### BLE Role

MyQ devices act as **BLE peripherals** (advertisers). The MyQ mobile app acts as the central. The BLE interaction flow during commissioning is most likely:

1. Device broadcasts advertisement with local name `MyQ-XXX` and custom service UUID
2. App discovers device via BLE scan (filtered by local name pattern or service UUID)
3. App connects and discovers GATT services
4. App writes Wi-Fi credentials (SSID/password) to a GATT characteristic under the custom service
5. Device connects to Wi-Fi and registers with myQ cloud
6. BLE connection is dropped; all further control goes through the cloud (HTTP/OAuth myQ API v6)

A web-based fallback provisioning path also exists: the hub exposes a SoftAP Wi-Fi network named `MyQ-nnn`, and the user provides credentials via `setup.myqdevice.com`. This is independent of BLE, but uses the same `MyQ-nnn` naming convention.

After commissioning, the device continues advertising indefinitely (we observe ongoing sightings — see "Observed in adwatch" below). The purpose of post-commissioning advertising is unclear; candidates include re-pairing/re-discovery, future feature support, or simply that the radio remains in advertising mode by firmware default. It is **not** the basis of MyQ's "auto-open on arrival" feature, which is GPS-geofence-based.

### GATT Services (Speculative)

No public documentation exists for the GATT service structure. Based on the single custom service UUID and typical IoT commissioning patterns:

| Service UUID | Purpose (speculative) |
|-------------|----------------------|
| `26D91A37-C279-4D0F-96A1-532CE41CE0F6` | Commissioning / Wi-Fi provisioning |

Expected characteristics would typically include Wi-Fi SSID (write), Wi-Fi password (write, possibly encrypted), provisioning status (read/notify), and device info / firmware version (read).

### Security+ 2.0 (Wired Protocol)

The wired protocol between the garage door motor and wall controls uses Security+ 2.0, an encrypted rolling-code serial protocol. This has been reverse-engineered by the ratgdo project and Konnected's blaQ product:

- 2-wire serial bus between motor unit and accessories
- Encrypted rolling codes prevent replay attacks
- Supports: door open/close, light control, door position, obstruction detection
- Open-source implementations: ratgdo (ESP8266/ESP32), Konnected GDO blaQ (ESP32-S3)

### Cloud API (v6)

The myQ cloud API uses OAuth-based authentication and provides door state, door control, light control, and device diagnostics. The API is undocumented by Chamberlain and has been reverse-engineered by the community.

## Detection Significance

- Garage door opener — reveals the presence and proximity of a garage entry point
- Security consideration: detecting garage door openers in BLE range identifies controllable physical access points
- BLE range is limited, so detection implies close proximity to the garage
- MyQ devices broadcast continuously after commissioning (exact purpose unconfirmed; not the basis of MyQ's GPS-geofenced auto-open)

## Observed in adwatch (April 2026 Export)

| Field | Value |
|-------|-------|
| Devices seen | 3 (`MyQ-017`, `MyQ-75D`, `MyQ-EF0`) |
| Address type | random |
| Service UUID | `26D91A37-C279-4D0F-96A1-532CE41CE0F6` |
| Manufacturer data | `78082e00` (4 bytes on one device) |
| Sighting count | 124 over ~5 hours (MyQ-017) |
| RSSI range | -84 to -100 dBm |

All three devices advertise the same custom service UUID. The continuous advertisement pattern (124 sightings over 5 hours) indicates the BLE radio stays active after commissioning. The exact reason is unconfirmed — likely re-discovery / re-pairing support, given that MyQ's "arrive home and open" feature itself uses GPS geofencing through the cloud, not BLE. RSSI values (-84 to -100 dBm) suggest 10-30+ meters distance, consistent with garage-mounted devices observed from inside an adjacent home.

## References

- [MyQ App](https://www.myq.com/) — Chamberlain Group smart garage platform
- [Chamberlain Group](https://www.chamberlaingroup.com/) — manufacturer (also LiftMaster, Craftsman)
- [hjdhjd/myq](https://github.com/hjdhjd/myq) — Node.js implementation of the myQ cloud API (HTTP only, no BLE)
- [PaulWieland/ratgdo](https://github.com/PaulWieland/ratgdo) — Open-source ESP board for Security+ 2.0 (wired bus, not BLE)
- [Konnected GDO blaQ](https://konnected.io/products/smart-garage-door-opener-blaq-myq-alternative) — Commercial local-control alternative
- [Bluetooth SIG Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/) — Company ID `0x0878` = "The Chamberlain Group, Inc." (verified via Nordic-mirrored SIG database)
- [LiftMaster MyQ Hub Wi-Fi setup (Fluent docs)](https://help.fluenthome.com/en_US/liftmaster-myq-smart-garage-hub/connect-a-liftmaster-myq-smart-garage-hub-to-a-wi-fi-network) — confirms `MyQ-nnn` = last 3 chars of hub serial
- [myQ Connected Garage / vehicle integrations](https://www.myq.com/auto) — confirms proximity auto-open uses GPS geofencing, not BLE
