"""Tests for vendor lookup integration in explorer API."""

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.dashboard.app import create_app
from adwatch.dashboard.websocket import WebSocketManager
from adwatch.models import RawAdvertisement, Classification
from adwatch.registry import ParserRegistry
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations
from adwatch.storage.raw import RawStorage


@pytest.fixture
async def db(tmp_path):
    database = Database()
    await database.connect(str(tmp_path / "test.db"))
    await run_migrations(database)
    yield database
    await database.close()


@pytest.fixture
async def raw_storage(db):
    return RawStorage(db)


@pytest.fixture
async def client(raw_storage):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=ParserRegistry(),
        ws_manager=WebSocketManager(),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_ad(mac, manufacturer_data=None, address_type="random", **kw):
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address=mac,
        address_type=address_type,
        manufacturer_data=manufacturer_data,
        service_data=kw.get("service_data"),
        service_uuids=kw.get("service_uuids", []),
        local_name=kw.get("local_name"),
        rssi=kw.get("rssi", -60),
    )


class TestVendorInExplorerAds:
    @pytest.mark.asyncio
    async def test_ads_include_vendor_name(self, client, raw_storage):
        """Ads with known company_id should have vendor_name."""
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad, Classification("apple", "phone", "company_id"))
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["vendor_name"] == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_ads_include_bt_company_name(self, client, raw_storage):
        """bt_company_name should be present in list results."""
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x06\x00\x01\x09")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        assert data[0]["bt_company_name"] == "Microsoft"

    @pytest.mark.asyncio
    async def test_ads_oui_for_public_mac(self, client, raw_storage):
        """Public MAC should have oui_vendor."""
        ad = _make_ad("00:03:93:DD:EE:01", address_type="public")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        assert data[0]["oui_vendor"] == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_ads_no_oui_for_random_mac(self, client, raw_storage):
        """Random MAC should have null oui_vendor."""
        ad = _make_ad("FA:FB:FC:DD:EE:01", address_type="random")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        assert data[0]["oui_vendor"] is None

    @pytest.mark.asyncio
    async def test_vendor_name_prefers_bt_over_oui(self, client, raw_storage):
        """vendor_name should prefer BT SIG company over OUI."""
        ad = _make_ad(
            "00:03:93:DD:EE:01",
            address_type="public",
            manufacturer_data=b"\x06\x00\x01\x09",  # Microsoft company ID
        )
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        # vendor_name should be Microsoft (from BT SIG), not Apple (from OUI)
        assert data[0]["vendor_name"] == "Microsoft"
        assert data[0]["bt_company_name"] == "Microsoft"
        assert data[0]["oui_vendor"] == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_ads_no_vendor_for_unknown(self, client, raw_storage):
        """Unknown company and random MAC should have null vendor_name."""
        ad = _make_ad("FA:FB:FC:DD:EE:01", manufacturer_data=b"\xad\xde\x01\x02")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads")
        data = resp.json()
        assert data[0]["vendor_name"] is None
        assert data[0]["bt_company_name"] is None


class TestVendorInExplorerDetail:
    @pytest.mark.asyncio
    async def test_detail_includes_all_vendor_fields(self, client, raw_storage):
        """Detail view should include vendor_name, bt_company_name, oui_vendor."""
        ad = _make_ad(
            "00:03:93:DD:EE:01",
            address_type="public",
            manufacturer_data=b"\x4c\x00\x10\x05",
        )
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ad/1")
        data = resp.json()
        assert data["vendor_name"] == "Apple, Inc."
        assert data["bt_company_name"] == "Apple, Inc."
        assert data["oui_vendor"] == "Apple, Inc."

    @pytest.mark.asyncio
    async def test_detail_vendor_fields_for_service_only_ad(self, client, raw_storage):
        """Ads with no manufacturer_data should still get oui_vendor if public."""
        ad = _make_ad(
            "00:02:B3:DD:EE:01",
            address_type="public",
            service_uuids=["fe9f"],
        )
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ad/1")
        data = resp.json()
        assert data["bt_company_name"] is None
        assert data["oui_vendor"] == "Intel Corporation"
        assert data["vendor_name"] == "Intel Corporation"


class TestVendorInFacets:
    @pytest.mark.asyncio
    async def test_facets_include_company_names(self, client, raw_storage):
        """Company ID facets should include the vendor name."""
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/facets")
        data = resp.json()
        cids = data["company_ids"]
        assert len(cids) == 1
        assert cids[0]["value"] == 0x004C
        assert cids[0]["name"] == "Apple, Inc."
