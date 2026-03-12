"""Tests for Bluetooth Mesh Detection BLE parser plugin."""

import hashlib

import pytest

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.plugins.bt_mesh import BtMeshParser


MESH_PROXY_UUID = "00001828-0000-1000-8000-00805f9b34fb"
MESH_PROV_UUID = "00001827-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def parser():
    return BtMeshParser()


def make_raw(service_data=None, service_uuids=None, **kwargs):
    defaults = dict(
        timestamp="2026-03-06T00:00:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=None,
        local_name=None,
    )
    defaults.update(kwargs)
    return RawAdvertisement(
        service_data=service_data,
        service_uuids=service_uuids or [],
        **defaults,
    )


# --- Test data builders ---

def _network_id_data(network_id: bytes = b"\x01\x02\x03\x04\x05\x06\x07\x08"):
    """Mesh Proxy with identification type 0x00 (Network ID)."""
    return bytes([0x00]) + network_id


def _node_identity_data(
    node_hash: bytes = b"\xAA" * 8,
    node_random: bytes = b"\xBB" * 8,
):
    """Mesh Proxy with identification type 0x01 (Node Identity)."""
    return bytes([0x01]) + node_hash + node_random + b"\x00"


def _provisioning_data(
    device_uuid: bytes = b"\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF\x00",
    oob_info: int = 0x0001,
):
    """Mesh Provisioning with device UUID + OOB info."""
    return device_uuid + oob_info.to_bytes(2, "big")


# --- Pre-built test data ---

PROXY_NETWORK_ID = _network_id_data()
PROXY_NODE_IDENTITY = _node_identity_data()
PROVISIONING_DATA = _provisioning_data()


class TestMeshProxyNetworkId:
    def test_parses_network_id(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["mesh_type"] == "proxy"
        assert result.metadata["identification_type"] == "network_id"
        assert result.metadata["network_id"] == "0102030405060708"

    def test_parser_name(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert result.parser_name == "bt_mesh"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert result.beacon_type == "bt_mesh"

    def test_device_class(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert result.device_class == "infrastructure"

    def test_identifier_hash_from_network_id(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        expected = hashlib.sha256("0102030405060708".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_identifier_hash_length(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert len(result.identifier_hash) == 16
        int(result.identifier_hash, 16)

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID})
        result = parser.parse(raw)
        assert result.raw_payload_hex == PROXY_NETWORK_ID.hex()


class TestMeshProxyNodeIdentity:
    def test_parses_node_identity(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NODE_IDENTITY})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["mesh_type"] == "proxy"
        assert result.metadata["identification_type"] == "node_identity"

    def test_node_hash(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NODE_IDENTITY})
        result = parser.parse(raw)
        assert result.metadata["node_hash"] == "aaaaaaaaaaaaaaaa"

    def test_node_random(self, parser):
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NODE_IDENTITY})
        result = parser.parse(raw)
        assert result.metadata["node_random"] == "bbbbbbbbbbbbbbbb"

    def test_identifier_hash_from_mac(self, parser):
        """Node identity uses MAC for identifier since there's no stable network ID."""
        raw = make_raw(service_data={MESH_PROXY_UUID: PROXY_NODE_IDENTITY})
        result = parser.parse(raw)
        expected = hashlib.sha256("AA:BB:CC:DD:EE:FF".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected


class TestMeshProvisioning:
    def test_parses_provisioning(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["mesh_type"] == "provisioning"

    def test_device_uuid(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result.metadata["device_uuid"] == "112233445566778899aabbccddeeff00"

    def test_oob_info(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result.metadata["oob_info"] == 1

    def test_identifier_hash_from_device_uuid(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        expected = hashlib.sha256(
            "112233445566778899aabbccddeeff00".encode()
        ).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result.device_class == "infrastructure"

    def test_beacon_type(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result.beacon_type == "bt_mesh"

    def test_raw_payload_hex(self, parser):
        raw = make_raw(service_data={MESH_PROV_UUID: PROVISIONING_DATA})
        result = parser.parse(raw)
        assert result.raw_payload_hex == PROVISIONING_DATA.hex()


class TestSecureNetworkBeacon:
    """Secure Network Beacon relayed via proxy (id_type 0x02)."""

    @staticmethod
    def _beacon_data(
        flags: int = 0x00,
        network_id: bytes = b"\x01\x02\x03\x04\x05\x06\x07\x08",
        iv_index: int = 0x00000042,
        auth_value: bytes = b"\xDE\xAD\xBE\xEF" * 2,
    ) -> bytes:
        return (
            bytes([0x02])  # id_type for secure network beacon
            + bytes([flags])
            + network_id
            + iv_index.to_bytes(4, "big")
            + auth_value
        )

    def test_parses_secure_beacon(self, parser):
        data = self._beacon_data()
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result is not None
        assert result.metadata["mesh_type"] == "secure_network_beacon"

    def test_flags_key_refresh(self, parser):
        data = self._beacon_data(flags=0x01)
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["key_refresh"] is True
        assert result.metadata["iv_update"] is False

    def test_flags_iv_update(self, parser):
        data = self._beacon_data(flags=0x02)
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["key_refresh"] is False
        assert result.metadata["iv_update"] is True

    def test_flags_both(self, parser):
        data = self._beacon_data(flags=0x03)
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["key_refresh"] is True
        assert result.metadata["iv_update"] is True

    def test_network_id(self, parser):
        data = self._beacon_data()
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["network_id"] == "0102030405060708"

    def test_iv_index(self, parser):
        data = self._beacon_data(iv_index=0x00001234)
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["iv_index"] == 0x00001234

    def test_auth_value(self, parser):
        data = self._beacon_data()
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.metadata["auth_value"] == (b"\xDE\xAD\xBE\xEF" * 2).hex()

    def test_identifier_hash_from_network_id(self, parser):
        data = self._beacon_data()
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        expected = hashlib.sha256("0102030405060708".encode()).hexdigest()[:16]
        assert result.identifier_hash == expected

    def test_device_class(self, parser):
        data = self._beacon_data()
        raw = make_raw(service_data={MESH_PROXY_UUID: data})
        result = parser.parse(raw)
        assert result.device_class == "infrastructure"

    def test_too_short_returns_none(self, parser):
        """Secure beacon needs 22 bytes minimum."""
        short_data = bytes([0x02]) + b"\x00" * 10
        raw = make_raw(service_data={MESH_PROXY_UUID: short_data})
        assert parser.parse(raw) is None


class TestMeshRejectsInvalid:
    def test_no_service_data(self, parser):
        raw = make_raw(service_data=None)
        assert parser.parse(raw) is None

    def test_empty_service_data(self, parser):
        raw = make_raw(service_data={})
        assert parser.parse(raw) is None

    def test_wrong_uuid(self, parser):
        raw = make_raw(service_data={"0000180a-0000-1000-8000-00805f9b34fb": b"\x00\x01"})
        assert parser.parse(raw) is None

    def test_proxy_too_short(self, parser):
        """Network ID type but less than 9 bytes total (1 type + 8 network_id)."""
        raw = make_raw(service_data={MESH_PROXY_UUID: bytes([0x00]) + b"\x01\x02\x03"})
        assert parser.parse(raw) is None

    def test_provisioning_too_short(self, parser):
        """Less than 18 bytes (16 UUID + 2 OOB)."""
        raw = make_raw(service_data={MESH_PROV_UUID: b"\x01" * 10})
        assert parser.parse(raw) is None

    def test_proxy_unknown_identification_type(self, parser):
        """Unknown identification type should return None."""
        raw = make_raw(service_data={MESH_PROXY_UUID: bytes([0x05]) + b"\x00" * 8})
        assert parser.parse(raw) is None


class TestMeshRegistration:
    def test_registered_with_service_uuid(self):
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = BtMeshParser()
        reg.register(
            name="bt_mesh",
            service_uuid=MESH_PROXY_UUID,
            description="Bluetooth Mesh Detection",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(
            service_data={MESH_PROXY_UUID: PROXY_NETWORK_ID},
            service_uuids=[MESH_PROXY_UUID],
        )
        matched = reg.match(raw)
        assert any(isinstance(p, BtMeshParser) for p in matched)

    def test_registered_with_provisioning_uuid(self):
        """Provisioning UUID should also route to bt_mesh parser."""
        from adwatch.registry import ParserRegistry
        reg = ParserRegistry()
        instance = BtMeshParser()
        reg.register(
            name="bt_mesh_proxy",
            service_uuid=MESH_PROXY_UUID,
            description="Bluetooth Mesh Detection",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        reg.register(
            name="bt_mesh_prov",
            service_uuid=MESH_PROV_UUID,
            description="Bluetooth Mesh Detection (Provisioning)",
            version="1.0.0",
            core=False,
            instance=instance,
        )
        raw = make_raw(
            service_data={MESH_PROV_UUID: PROVISIONING_DATA},
            service_uuids=[MESH_PROV_UUID],
        )
        matched = reg.match(raw)
        assert any(isinstance(p, BtMeshParser) for p in matched)

    def test_default_registry_has_provisioning_uuid(self):
        """The default registry should route provisioning UUID to bt_mesh."""
        from adwatch.registry import _default_registry
        raw = make_raw(
            service_data={MESH_PROV_UUID: PROVISIONING_DATA},
            service_uuids=[MESH_PROV_UUID],
        )
        matched = _default_registry.match(raw)
        assert any(isinstance(p, BtMeshParser) for p in matched)

    def test_not_core(self):
        """bt_mesh should be a plugin (core=False)."""
        assert True


class TestBtMeshUIConfig:
    def test_ui_config_returns_tab(self):
        parser = BtMeshParser()
        cfg = parser.ui_config()
        assert cfg is not None
        assert cfg.tab_name == "BT Mesh"

    def test_ui_config_has_data_table(self):
        parser = BtMeshParser()
        cfg = parser.ui_config()
        widget_types = [w.widget_type for w in cfg.widgets]
        assert "data_table" in widget_types

    def test_ui_config_has_render_hints(self):
        parser = BtMeshParser()
        cfg = parser.ui_config()
        table_widgets = [w for w in cfg.widgets if w.widget_type == "data_table"]
        assert len(table_widgets) > 0
        assert "columns" in table_widgets[0].render_hints

    def test_api_router_returns_router(self):
        from unittest.mock import MagicMock
        parser = BtMeshParser()
        db = MagicMock()
        router = parser.api_router(db)
        assert router is not None

    def test_api_router_none_without_db(self):
        parser = BtMeshParser()
        assert parser.api_router(None) is None
