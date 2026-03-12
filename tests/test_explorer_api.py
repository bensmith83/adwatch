"""Tests for Protocol Explorer API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from adwatch.dashboard.app import create_app
from adwatch.dashboard.routers.explorer import create_explorer_router
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
def registry():
    return ParserRegistry()


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
async def client(raw_storage, registry, ws_manager):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=registry,
        ws_manager=ws_manager,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_ad(mac, manufacturer_data=None, service_uuids=None, local_name=None,
             rssi=-60, service_data=None, timestamp="2025-01-15T10:30:00+00:00"):
    return RawAdvertisement(
        timestamp=timestamp,
        mac_address=mac,
        address_type="random",
        manufacturer_data=manufacturer_data,
        service_data=service_data,
        service_uuids=service_uuids or [],
        local_name=local_name,
        rssi=rssi,
    )


async def _seed_ads(raw_storage):
    """Insert test ads."""
    ad1 = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05\x01")
    await raw_storage.save(ad1, Classification("apple_nearby", "phone", "company_id"),
                           parsed_by=["apple_continuity"])

    ad2 = _make_ad("MS:CD:P0:00:00:01", manufacturer_data=b"\x06\x00\x01\x09\x20")
    await raw_storage.save(ad2, Classification("microsoft_cdp", "laptop", "company_id"),
                           parsed_by=["microsoft_cdp"])

    ad3 = _make_ad("00:11:22:33:44:55", manufacturer_data=b"\xff\xff\x01\x02")
    await raw_storage.save(ad3)


# ===================================================================
# GET /api/explorer/ads
# ===================================================================

class TestExplorerAdsEndpoint:
    @pytest.mark.asyncio
    async def test_empty_db_returns_200(self, client):
        resp = await client.get("/api/explorer/ads")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_ads_with_derived_fields(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Check derived fields present
        apple_ad = [a for a in data if a["ad_type"] == "apple_nearby"][0]
        assert "company_id_int" in apple_ad
        assert apple_ad["company_id_int"] == 76

    @pytest.mark.asyncio
    async def test_filter_by_ad_type(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads", params={"ad_type": "apple_nearby"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["ad_type"] == "apple_nearby"

    @pytest.mark.asyncio
    async def test_filter_by_parsed_by(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads", params={"parsed_by": "microsoft_cdp"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_local_name(self, client, raw_storage):
        ad = _make_ad("11:22:33:44:55:66", local_name="TP357 (2B54)")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ads", params={"local_name": "TP357"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_mac_prefix(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads", params={"mac_prefix": "AA:BB"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_filter_by_min_sightings(self, client, raw_storage):
        await _seed_ads(raw_storage)
        # All ads have sighting_count=1, so min_sightings=2 should return none
        resp = await client.get("/api/explorer/ads", params={"min_sightings": 2})
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    @pytest.mark.asyncio
    async def test_limit(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads", params={"limit": 1})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_default_limit(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/ads")
        assert resp.status_code == 200
        # Default limit should be reasonable (e.g. 100)
        assert len(resp.json()) <= 100


# ===================================================================
# GET /api/explorer/ad/{id}
# ===================================================================

class TestExplorerAdDetailEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_for_valid_id(self, client, raw_storage):
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ad/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_id(self, client):
        resp = await client.get("/api/explorer/ad/9999")
        assert resp.status_code == 404


# ===================================================================
# GET /api/explorer/facets
# ===================================================================

class TestExplorerFacetsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_with_facets(self, client, raw_storage):
        await _seed_ads(raw_storage)
        resp = await client.get("/api/explorer/facets")
        assert resp.status_code == 200
        data = resp.json()
        assert "ad_types" in data
        assert "company_ids" in data
        assert len(data["ad_types"]) > 0

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_facets(self, client):
        resp = await client.get("/api/explorer/facets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ad_types"] == []
        assert data["company_ids"] == []


# ===================================================================
# GET /api/explorer/compare
# ===================================================================

class TestExplorerCompareEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200_with_comparison(self, client, raw_storage):
        ad1 = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        ad2 = _make_ad("AA:BB:CC:DD:EE:02", manufacturer_data=b"\x4c\x00\x10\x07")
        await raw_storage.save(ad1)
        await raw_storage.save(ad2)
        resp = await client.get("/api/explorer/compare", params={"ids": "1,2"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_returns_empty_for_invalid_ids(self, client):
        resp = await client.get("/api/explorer/compare", params={"ids": "9999,8888"})
        assert resp.status_code == 200
        assert resp.json() == []
