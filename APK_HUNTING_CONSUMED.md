# apk-ble-hunting Passive Report Consumption

Tracks which `*_passive.md` byte-level advertisement guides from the sibling
`apk-ble-hunting` project have been consumed into adwatch parsers/plugins.

- **Source dir**: `/home/pi/xfer/vibin/apk-ble-hunting/reports/`
- **Report shape**: one `<slug>_passive.md` per target, byte-level decode of
  manufacturer data, service data, and device name. See the project CLAUDE.md
  for the full stage-4b pipeline.
- **Expect more**: this list grows as the apk-ble-hunting project batches new
  targets. When kicking off work, re-`ls` the reports dir and append any new
  `*_passive.md` entries below with status `pending`.

## Status legend

- **consumed** — report read, findings merged into an adwatch parser/plugin,
  no further work expected from it
- **covered** — adwatch already has a matching plugin that predates the
  report; still needs a pass to cross-check/enrich from the report
- **pending** — report exists, not yet reviewed
- **skip** — intentionally not pursued (connection-only, encrypted, no useful
  passive shape); reason noted inline

## Workflow

1. Pick a `pending` row.
2. Read `reports/<slug>_passive.md`. If it documents a useful passive shape
   (manufacturer-data prefix, service-UUID, service-data layout, or name
   regex), add/extend a plugin under `src/adwatch/plugins/`.
3. Flip to `consumed`, note the plugin file, and add a short note on what was
   actually usable.
4. If it's connection-only or encrypted-opaque, mark `skip` with reason.

## Report inventory

| # | Slug | Category | Status | adwatch plugin | Notes |
|---|------|----------|--------|----------------|-------|
| 1 | agilexrobotics-mammotion | robotic mower | consumed | `plugins/mammotion.py` (new) | company_id 0x01A8 + name regex (Luba/Yuka/Spino/RTK/etc.); product-id 4-byte ASCII decode (HM430/MN232/PC100); MAC in payload per subtype |
| 2 | aiper-link | pool cleaner | consumed | `plugins/aiper.py` (new) | name prefix `Aiper` + protocol-flag byte extraction; minimal passive surface (connection-only state) |
| 3 | allegion-leopard | smart lock (Schlage) | consumed | `plugins/schlage.py` (new) | uWeave service UUID `1f6b43aa-…` + name regex (SENSE/schlage/NDE/Walton/GSELENT/SSELENT); Encode serial extraction from `schlage<serial>` name |
| 4 | anovaculinary-android | sous vide | consumed | `plugins/anova.py` (new) | Neuron (`0e140000-…`) + SDK (`09fa0000-…`) service UUIDs + name prefix; no passive telemetry |
| 5 | apptionlabs-meater-app | meat thermometer | consumed | `plugins/meater.py` | **major upgrade from detection-only**: 11 service UUIDs (4 probe + 7 block variants); 28-entry product-type table; block status-mode decode; 3-path parser (block-normal 8B / keep-alive 10B / probe 9B); name fallback `<hex_type>-<hex_id>`; identity hash uses stable 64-bit device_id |
| 6 | ascensia-contour-us | glucose meter | consumed | `plugins/ascensia_contour.py` (new) | company_id 0x0167 + name `^(Contour\|Portal)`; detection-only (no passive state) |
| 7 | assaabloy-yale | smart lock | consumed | `plugins/august_yale.py` | added `0x0016` company + V1/V2/V4 service UUIDs + keypad service UUIDs; 16-byte LockID extraction (2-byte-header + tail-aligned); generation V1/V2/V3/V4 from UUID; keypad-serial regex → device_kind + identity hash |
| 8 | august-luna | smart lock | consumed | `plugins/august_yale.py` | merged with Yale; identity now prefers stable LockID over mac+name |
| 9 | barkinglabs-fi | pet tracker | consumed | `plugins/barkinglabs_fi.py` (new) | 3 service UUIDs `57b40001/0210/3001-…` → role tagging (collar / base_config / base_proxy) |
| 10 | bosch-toolbox2 | power tools | consumed | `plugins/bosch_toolbox.py` (new) | 8 service UUIDs mapped to category (power_tool/measuring_tool/floodlight) + family (COMO 1.0/1.1/2.0, GCL, MIRX, Helios, EOS); byte-level tool-state decode deferred (needs raw scan record) |
| 11 | bose-bosemusic | audio | consumed | `plugins/bose.py` | **Fixed wrong IDs**: company `0x0065` (Lenovo)→`0x009E`, removed junk `0x3703`; service UUID `fe78` (Garmin)→`febe`; service data `fdf7` (Weber)→`febe`. Added BMAP UUID + `^Bose ` name matcher + `model_hint` metadata. Updated 2 legacy test files locked to wrong constants. |
| 12 | chipolo-net-v3 | tracker tag | consumed | `plugins/chipolo.py` | added `fe65` (current) + `fd44` (FMDN) service UUIDs; variant tagging (legacy/current/fmdn_a/fmdn_b/fmdn); 8-byte FMDN prefix detection + rotating-ID extraction; exported `CHIPOLO_PROXIMITY_UUID` for downstream iBeacon enrichment |
| 13 | concept2-ergdata | rowing machine | consumed | `plugins/concept2_pm5.py` (new) | name contains `PM5` or starts `Concept2`; passive report notes app uses legacy scan API so no byte parsing available |
| 14 | dexcom-g6 | CGM | consumed | `plugins/dexcom_cgm.py` | **Fixed wrong UUID** (was `61ce1c20-...`, now SIG `febc`); G6 name regex `^Dexcom[A-Z0-9]{2}$`; serial-tail extraction → identity hash `dexcom_g6:<XX>` |
| 15 | dexcom-g7 | CGM | consumed | `plugins/dexcom_cgm.py` | G7 community UUID `f8083532-...`; name prefix `DXCM`; model detection from UUID or name |
| 16 | ecobee-athenamobile | thermostat | consumed | `plugins/ecobee.py` (new) | `ecobee Inc. - <serial>` name pattern; serial-prefix → product family (61/63 thermostat, 71 THEIA camera, 72 HECATE contact) |
| 17 | embertech | smart mug | consumed | `plugins/ember_mug.py` | added vendor service UUIDs (`fc543621-…` original, `fc543622-…` ceramic); generation tagging; Nordic DFU UUID detection |
| 18 | evehome-eve | HomeKit accessories | covered | `plugins/matter.py` | Eve delegates BLE to Google Home APIs; existing matter plugin handles the `fff6` commissioning ads. Eve VID = 0x131D per CSA DCL registry (not currently mapped in matter plugin — future enrichment) |
| 19 | fitbit-fitbitmobile | wearable | consumed | `plugins/fitbit.py` | added primary service UUIDs (`fd62` SIG, `abbaff00-…` Gattlink, `26f33a00-…` Aria); product-line tagging from name; kept speculative Qualcomm-0x000A mfr path as best-effort |
| 20 | fixdapp-two | OBD-II scanner | consumed | `plugins/fixd_obd2.py` | **identification shifted to MAC-prefix list** per Android app: 7 OUI/prefix rules → `sensor_model` (OLD_KICKSTARTER / SETOSMART / VIECAR / VIECAR_V2); dropped name-required gate |
| 21 | flir-tools | thermal imager | consumed | `plugins/flir_tools.py` (new) | company_id 0x0AE9 (FLIR One) + Meterlink UUID + name prefix; byte-level decode deferred (native lib) |
| 22 | fluke-deviceapp | multimeter | consumed | `plugins/fluke.py` (new) | Fluke UUID base `b698XXXX-7562-11e2-b50d-00163e46f8fe` regex + name `^Fluke`; instrument-family code from variable XXXX |
| 23 | freestylelibre3-app-us | CGM | consumed | `plugins/freestyle_libre3.py` (new) | Abbott Libre 3 UUID base `0898XXXX-ef89-11e9-81b4-2a2ae2dbcce4` + name regex (`FreeStyle Libre 3`/`ABBOTT`/`LIBRE3`); limited passive surface since app uses direct-connect-by-MAC |
| 24 | gardena-smartgarden | irrigation | skip | — | Capacitor/hybrid app delegates BLE to remote web bundle (`bff-api.sg.dss.husqvarnagroup.net`); no BLE constants in APK. Re-visit if remote bundle is fetched |
| 25 | garmin-apps-connectmobile | wearable | consumed | `plugins/garmin.py` | added modern (`fe1f`) + legacy (`00001001-7791-…`) service UUIDs; 23-family name-prefix regex (Forerunner/fenix/Edge/vivo/venu/…); device-class refinement (HR monitor, power meter, satellite messenger) |
| 26 | govee-home | sensors/lights | consumed | `plugins/govee.py`, `plugins/govee_led.py` | added `ec88` service UUID to govee sensor plugin for UUID-only detection; existing rich mfr-data parsing (H5074/H5075/H5103/H5177/H5181/H512x) preserved |
| 27 | greenworks-tools | outdoor tools | consumed | `plugins/greenworks.py` (new) | unregistered company_id 0x15A8 + name regex (greenworks/gwelite/cramer) + MAC OUIs (34:12:/45:09:/A8:15:); brand tagging |
| 28 | huahuacaocao-flowercare | plant sensor | covered | `plugins/mibeacon.py` | Xiaomi HHCC uses MiBeacon service UUID `0xFE95` — already handled by our mibeacon plugin (product IDs 0x0098/0x015D/0x03BC/0x03BD) |
| 29 | husqvarna-automowerconnect | robotic mower | consumed | `plugins/husqvarna.py` (new) | service UUID `98bd0001-…` + company_id 0x0426; full TLV parser (length-type-value stream) extracts serial_number, state (9 values), activity (7 values), device_group (6 values), pairing flag; **rich live operational telemetry** |
| 30 | insulet-myblue-pdm | insulin pump | consumed | `plugins/insulet_omnipod.py` (new) | name-based detection only (TWI SDK uses dynamically-resolved company ID and native byte parsing — not recoverable from Java) |
| 31 | irobot-home | robot vacuum | consumed | `plugins/irobot.py` (new) | name regex (Altadena/iRobot Braav/Roomba) + service UUID `0bd51777-…` + mfr-data magic `A8 01 ?? 31 10`; disambiguates from Mammotion which shares company_id 0x01A8 |
| 32 | kinsa-polaris-app | smart thermometer | consumed | `plugins/kinsa.py` (new) | UUID regex `^[0-9a-f]{8}-[0-9a-f]{4}-746c-6165-4861736e694b$` (ASCII "Kinsa Health" fragment) + name prefixes (Kinsa/AViTA/KS_) |
| 33 | kwikset-blewifi | smart lock | consumed | `plugins/kwikset.py` (new) | 4 variants (consumer/auraReach/halo3/multifamily) with different mfr-data byte offsets; 9-byte `unique_id` + product_id + protocol_version + notification indices; halo3 exposes live `lock_status_info` (locked/unlocked/jammed) |
| 34 | lifx-lifx | smart bulb | skip | — | app version in this batch has no BLE (WiFi-only setup) — no BLE-layer advertisement exists to parse |
| 35 | masimo-merlin-consumer | pulse ox | consumed | `plugins/masimo.py` (new) | company_id 0x0243 + `MightySat`/`Masimo` name; exposes protocol_version byte (offsets inside mfr data obfuscated, not decoded) |
| 36 | maytronics-app | pool cleaner | consumed | `plugins/maytronics.py` (new) | multi-path name regex (IoT_PWS/maytronics00/MxX_pws/bare 8-char serial/12-char hex) + 6-byte mfr-data layout (model_code/proto/serial-hash/mu-version) |
| 37 | milwaukeetool-mymilwaukee | power tools | consumed | `plugins/milwaukee_onekey.py` (new) | company_id 0x0604 + SIG UUID `fdf5` + legacy 128-bit UUID; raw payload hex exposed (field-level decode not recoverable from APK) |
| 38 | nuki | smart lock | consumed | `plugins/nuki.py` (new) | 9 service UUIDs across 5 product families (lock/bridge/fob/box/keypad); role/state tagging (advertising/pairing/keyturner/firmware_update); pairing-mode detection |
| 39 | orbit-smarthome | irrigation | consumed | `plugins/orbit_bhyve.py` (new) | name regex `^bhyve_[0-9a-f]{6}$` + vendor-UUID-base pattern `*-fe32-4f58-8b78-98e42b2c047f`; device-id suffix as identity |
| 40 | pg-oralb-oralbapp | toothbrush | consumed | `plugins/oralb.py` | **Fixed off-by-2 byte layout**: fields were shifted — "state/pressure/minutes/seconds" were actually deviceType/softwareVersion/deviceState/status. Correct layout: protocolVersion(0) deviceType(1) softwareVersion(2) deviceState(3) statusByte(4) brushTimeMin(5) brushTimeSec(6). Added 37-model DEVICE_TYPES table, full 13-state DEVICE_STATES, status-byte bit unpack (pressure/power-btn/mode-btn) |
| 41 | philips-lighting-hue2 | smart bulb | skip | — | passive report says the `com.philips.lighting.hue2` app has no BLE functionality at all; Hue bulbs would be handled by the separate `com.signify.hue.blue` app which wasn't processed |
| 42 | polar-polarflow | HR/wearable | consumed | `plugins/polar.py` (new) | company_id 0x006B + service UUID `feee` + name regex; PbMasterIdentifierBroadcast parse (SF byte validation, user_id_len, reversed-BigInteger Flow user ID); payload-length tier hint (13=watch, 11=strap); GoPro-paired flag |
| 43 | positec-landroid | robotic mower | consumed | `plugins/worx_landroid.py` (new) | service UUID `abf0` only; state behind GATT — passive scanner detects presence, not state |
| 44 | rachio-iro | irrigation | skip | — | Rachio controllers are WiFi-only; no BLE radio. Matter code in APK is vendored-dead |
| 45 | rainbird-rainbird2 | irrigation | consumed | `plugins/rainbird.py` (new) | 3 detection paths: name contains RAINBIRD (LNK2/RC2), regex `^BAT-(BT\|PRO)-(\d+)I?$` (ESP-BAT with zone count), Solem 128-bit UUIDs |
| 46 | rivian-android-consumer | vehicle/phone key | consumed | `plugins/rivian.py` | already correct — company ID 0x0941 matches; passive report confirms obfuscated byte layout, no additions safely derivable |
| 47 | segway-mower | robotic mower | consumed | `plugins/segway_navimow.py` (new) | unregistered company_id 0x4E42 (ASCII "NB"); BLE type byte (0xE0 mower / 0x23 MowGate), protocol-version ≥ 2 gate, 1's-complement checksum validation; FindMy variant exposes serial in cleartext |
| 48 | sphero-sprk | robot toy | consumed | `plugins/sphero.py` | added 6-model prefix map (BB=BB-8, GB=BB-9E, SK=SPRK+, SB=BOLT, SM=Mini, RV=RVR); added v1 (`22bb746f-…`) + v2 initializer (`00020001-574f-…`) service UUIDs; stable identity hash via model+device_id |
| 49 | swordhealth-guarda | health wearable | skip | — | Passive report shows the app only filters on generic `0xFFF0` (JStyle SDK) which many unrelated BLE devices use; registering would cause false positives with no Sword-specific signal to disambiguate |
| 50 | teslamotors-tesla | vehicle/phone key | consumed | `plugins/tesla.py` (new) | service UUID 0x1122 + `S.{3,}` name filter; model char at index 3 (3/Y/S/X/C/R/D/P); VIN-hash fragment = name[3:] used as stable identity |
| 51 | thetileapp-tile | tracker tag | consumed | `plugins/tile.py` | added `feec` (PrivateID / current) alongside `feed` (legacy); variant tagging (legacy/privateid); exact byte-offset parsing of hashedId/counter/tx_power deferred (PairIP-obfuscated in APK) |
| 52 | tpky-mc | Tapkey Mobile lock | consumed | `plugins/tapkey.py` (new) | **vendor identified: Tapkey (not TP-Link)** — service UUID `6e65742e-7470-6b79-2ea0-000006060101` (ASCII "net.tpky.") + mfr-data magic byte `(magic & 0x7F)==1`; bit 7 = lockId-incomplete flag |
| 53 | tractive-android-gps | pet tracker | consumed | `plugins/tractive.py` (new) | 4 per-family UUIDs (Cat/Dog/V2/Fw4); 12-name DFU-mode detection (TRDOG1/TRCAT1/TG4410/TG5/TG6A/etc.) with `dfu_model_code` metadata |
| 54 | traegergrills-app | smart grill | consumed | `plugins/traeger.py` (new) | name prefix `Yosemite` + provisioning UUID `a8220000-…`; model-code decode from raw scan record deferred (needs raw bytes not in RawAdvertisement) |
| 55 | volvo-vcc | vehicle/phone key | consumed | `plugins/volvo.py` (new) | Volvo uses Apple iBeacon wrapper (company_id 0x004C) with fleet-wide proximity UUID `e20a39f4-73f5-4bc4-1864-17d1ad07a962`; major/minor (big-endian) carry per-vehicle SKI fragment → used as stable identity |
| 56 | withings-wiscale2 | smart scale | consumed | `plugins/withings.py` (new) | SIG UUIDs 0x9990-0x9999 mapped to 5 product models (scales/BPM/etc.); "WITH" (0x5749 0x5448) marker detection on custom UUIDs; manufacturer-data MAC → provisioning state (unprovisioned/provisioning/paired); name-prefix matchers (bl_hwa, WSM02, WBS0x, WPM0x) |

## Summary (as of 2026-04-16)

- Total reports: **56**
- consumed: **46**
- covered (pre-existing plugin): **2**
- pending: **0**
- skip: **5**
