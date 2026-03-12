"""Bluetooth Mesh Detection BLE advertisement parser."""

import hashlib

from adwatch.models import RawAdvertisement, ParseResult, PluginUIConfig, WidgetConfig, deserialize_service_data
from adwatch.registry import register_parser, _default_registry

MESH_PROXY_UUID = "00001828-0000-1000-8000-00805f9b34fb"
MESH_PROV_UUID = "00001827-0000-1000-8000-00805f9b34fb"

IDENTIFICATION_NETWORK_ID = 0x00
IDENTIFICATION_NODE_IDENTITY = 0x01

IDENTIFICATION_SECURE_BEACON = 0x02

MIN_NETWORK_ID_LEN = 9   # 1 type + 8 network_id
MIN_NODE_IDENTITY_LEN = 17  # 1 type + 8 hash + 8 random
MIN_PROVISIONING_LEN = 18  # 16 UUID + 2 OOB
MIN_SECURE_BEACON_LEN = 22  # 1 type + 1 flags + 8 network_id + 4 iv_index + 8 auth


@register_parser(
    name="bt_mesh",
    service_uuid=MESH_PROXY_UUID,
    description="Bluetooth Mesh Detection",
    version="1.0.0",
    core=False,
)
class BtMeshParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        if not raw.service_data:
            return None

        if MESH_PROXY_UUID in raw.service_data:
            return self._parse_proxy(raw, raw.service_data[MESH_PROXY_UUID])
        elif MESH_PROV_UUID in raw.service_data:
            return self._parse_provisioning(raw, raw.service_data[MESH_PROV_UUID])

        return None

    def _parse_proxy(self, raw: RawAdvertisement, data: bytes) -> ParseResult | None:
        if not data:
            return None

        id_type = data[0]

        if id_type == IDENTIFICATION_NETWORK_ID:
            if len(data) < MIN_NETWORK_ID_LEN:
                return None
            network_id = data[1:9].hex()
            id_hash = hashlib.sha256(network_id.encode()).hexdigest()[:16]
            return ParseResult(
                parser_name="bt_mesh",
                beacon_type="bt_mesh",
                device_class="infrastructure",
                identifier_hash=id_hash,
                raw_payload_hex=data.hex(),
                metadata={
                    "mesh_type": "proxy",
                    "identification_type": "network_id",
                    "network_id": network_id,
                },
            )
        elif id_type == IDENTIFICATION_NODE_IDENTITY:
            if len(data) < MIN_NODE_IDENTITY_LEN:
                return None
            node_hash = data[1:9].hex()
            node_random = data[9:17].hex()
            id_hash = hashlib.sha256(raw.mac_address.encode()).hexdigest()[:16]
            return ParseResult(
                parser_name="bt_mesh",
                beacon_type="bt_mesh",
                device_class="infrastructure",
                identifier_hash=id_hash,
                raw_payload_hex=data.hex(),
                metadata={
                    "mesh_type": "proxy",
                    "identification_type": "node_identity",
                    "node_hash": node_hash,
                    "node_random": node_random,
                },
            )
        elif id_type == IDENTIFICATION_SECURE_BEACON:
            return self._parse_secure_beacon(raw, data)

        return None

    def _parse_secure_beacon(self, raw: RawAdvertisement, data: bytes) -> ParseResult | None:
        if len(data) < MIN_SECURE_BEACON_LEN:
            return None

        flags = data[1]
        network_id = data[2:10].hex()
        iv_index = int.from_bytes(data[10:14], "big")
        auth_value = data[14:22].hex()
        id_hash = hashlib.sha256(network_id.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="bt_mesh",
            beacon_type="bt_mesh",
            device_class="infrastructure",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "mesh_type": "secure_network_beacon",
                "key_refresh": bool(flags & 0x01),
                "iv_update": bool(flags & 0x02),
                "network_id": network_id,
                "iv_index": iv_index,
                "auth_value": auth_value,
            },
        )

    def _parse_provisioning(self, raw: RawAdvertisement, data: bytes) -> ParseResult | None:
        if len(data) < MIN_PROVISIONING_LEN:
            return None

        device_uuid = data[:16].hex()
        oob_info = int.from_bytes(data[16:18], "big")
        id_hash = hashlib.sha256(device_uuid.encode()).hexdigest()[:16]

        return ParseResult(
            parser_name="bt_mesh",
            beacon_type="bt_mesh",
            device_class="infrastructure",
            identifier_hash=id_hash,
            raw_payload_hex=data.hex(),
            metadata={
                "mesh_type": "provisioning",
                "device_uuid": device_uuid,
                "oob_info": oob_info,
            },
        )

    def storage_schema(self):
        return None

    def api_router(self, db=None):
        if db is None:
            return None

        from fastapi import APIRouter, Query

        router = APIRouter()
        parser = self

        @router.get("/recent")
        async def recent(limit: int = Query(50, ge=1, le=500)):
            rows = await db.fetchall(
                "SELECT *, last_seen AS timestamp FROM raw_advertisements WHERE ad_type = ? ORDER BY last_seen DESC LIMIT ?",
                ("bt_mesh", limit),
            )
            enriched = []
            for row in rows:
                item = dict(row)
                svc_json = item.get("service_data_json")
                if svc_json:
                    try:
                        svc_data = deserialize_service_data(svc_json)
                        raw = RawAdvertisement(
                            timestamp=item["timestamp"],
                            mac_address=item["mac_address"],
                            address_type=item.get("address_type", "random"),
                            manufacturer_data=None,
                            service_data=svc_data,
                        )
                        result = parser.parse(raw)
                        if result:
                            item.update(result.metadata)
                    except (ValueError, KeyError):
                        pass
                enriched.append(item)
            return enriched

        return router

    def ui_config(self):
        return PluginUIConfig(
            tab_name="BT Mesh",
            tab_icon="network",
            widgets=[
                WidgetConfig(
                    widget_type="data_table",
                    title="Mesh Network Sightings",
                    data_endpoint="/api/bt_mesh/recent",
                    render_hints={"columns": ["timestamp", "mac_address", "mesh_type", "network_id", "rssi_max", "sighting_count"]},
                ),
            ],
        )


# Register for provisioning UUID too (decorator only supports one service_uuid)
_default_registry.register(
    name="bt_mesh_prov",
    service_uuid=MESH_PROV_UUID,
    description="Bluetooth Mesh Detection (Provisioning)",
    version="1.0.0",
    core=False,
    instance=BtMeshParser(),
)
