"""KS03 generic BLE HID remote parser.

Covers the ubiquitous "KS03~xxxxxx" family of unbranded Chinese BLE HID
peripherals (selfie shutters, phone page-turners, e-reader clickers, TikTok
scrollers). These devices emulate a BLE HID keyboard and typically send a
Volume-Up keycode, which triggers the camera shutter on iOS/Android.

They advertise with a recognizable fingerprint:
- local_name = "KS03~" + lower-6-hex (the low 3 bytes of the device MAC)
- service UUIDs: 0x1812 (HID over GATT), 0x180F (Battery Service)
- manufacturer_data = 0xF0 0x01 0x02 0x03 0x04 0x05 0x06 0x00 (an uninitialized
  Telink / Beken reference-SDK template, not real vendor data). Company ID
  0x01F0 resolves to Mobvoi per the Bluetooth SIG, but that is spoofing /
  copy-paste - these devices are not Mobvoi products.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig
from adwatch.registry import register_parser


KS03_NAME_PATTERN = r"^KS03~[0-9a-fA-F]{6}$"
KS03_NAME_RE = re.compile(KS03_NAME_PATTERN)
KS03_PLACEHOLDER_MFG = bytes.fromhex("f001020304050600")


@register_parser(
    name="ks03_hid_remote",
    local_name_pattern=KS03_NAME_PATTERN,
    description="Generic KS03 BLE HID remote (selfie shutter / page turner)",
    version="1.0.0",
    core=False,
)
class KS03HidRemoteParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if raw.local_name is None:
            return None
        match = KS03_NAME_RE.match(raw.local_name)
        if not match:
            return None

        mac_suffix = raw.local_name.split("~", 1)[1].lower()

        mfg_placeholder = raw.manufacturer_data == KS03_PLACEHOLDER_MFG

        metadata: dict = {
            "device_name": raw.local_name,
            "mac_suffix": mac_suffix,
            "mfg_placeholder": mfg_placeholder,
            "advertises_hid": "1812" in (raw.service_uuids or [])
            or "00001812-0000-1000-8000-00805f9b34fb" in (raw.service_uuids or []),
        }
        if mfg_placeholder:
            metadata["claimed_company_id"] = "0x01F0"

        id_hash = hashlib.sha256(
            f"{raw.mac_address}:ks03_hid_remote".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="ks03_hid_remote",
            beacon_type="ks03_hid_remote",
            device_class="remote",
            identifier_hash=id_hash,
            raw_payload_hex="",
            metadata=metadata,
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            return await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements "
                "WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("ks03_hid_remote", limit),
            )

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="KS03 Remotes",
            tab_icon="smartphone",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Recent KS03 Sightings",
                    data_endpoint="/api/ks03_hid_remote/recent",
                    render_hints={
                        "columns": [
                            "timestamp",
                            "mac_address",
                            "local_name",
                            "rssi_max",
                            "sighting_count",
                        ]
                    },
                ),
            ],
        )
