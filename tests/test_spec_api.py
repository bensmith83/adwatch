"""Tests for Protocol Specs API endpoints."""

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
def registry():
    return ParserRegistry()


@pytest.fixture
def ws_manager():
    return WebSocketManager()


@pytest.fixture
async def client(raw_storage, registry, ws_manager, db):
    app = create_app(
        raw_storage=raw_storage,
        classifier=None,
        registry=registry,
        ws_manager=ws_manager,
        db=db,
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


# ===================================================================
# POST /api/explorer/specs — create spec
# ===================================================================

class TestCreateSpec:
    @pytest.mark.asyncio
    async def test_create_spec(self, client):
        resp = await client.post("/api/explorer/specs", json={
            "name": "my_protocol",
            "description": "Test protocol",
            "company_id": 76,
            "data_source": "mfr",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my_protocol"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_spec_minimal(self, client):
        resp = await client.post("/api/explorer/specs", json={"name": "minimal"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "minimal"

    @pytest.mark.asyncio
    async def test_create_spec_duplicate_name_fails(self, client):
        await client.post("/api/explorer/specs", json={"name": "dup"})
        resp = await client.post("/api/explorer/specs", json={"name": "dup"})
        assert resp.status_code in (400, 409, 422)


# ===================================================================
# GET /api/explorer/specs — list specs
# ===================================================================

class TestListSpecs:
    @pytest.mark.asyncio
    async def test_list_specs_empty(self, client):
        resp = await client.get("/api/explorer/specs")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_specs(self, client):
        await client.post("/api/explorer/specs", json={"name": "proto1"})
        await client.post("/api/explorer/specs", json={"name": "proto2"})
        resp = await client.get("/api/explorer/specs")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ===================================================================
# GET /api/explorer/specs/{spec_id} — get spec with fields
# ===================================================================

class TestGetSpec:
    @pytest.mark.asyncio
    async def test_get_spec(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.get(f"/api/explorer/specs/{spec_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "proto1"
        assert "fields" in data

    @pytest.mark.asyncio
    async def test_get_spec_not_found(self, client):
        resp = await client.get("/api/explorer/specs/9999")
        assert resp.status_code == 404


# ===================================================================
# PUT /api/explorer/specs/{spec_id} — update spec
# ===================================================================

class TestUpdateSpec:
    @pytest.mark.asyncio
    async def test_update_spec(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.put(f"/api/explorer/specs/{spec_id}", json={"description": "updated"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "updated"

    @pytest.mark.asyncio
    async def test_update_spec_not_found(self, client):
        resp = await client.put("/api/explorer/specs/9999", json={"description": "nope"})
        assert resp.status_code == 404


# ===================================================================
# DELETE /api/explorer/specs/{spec_id} — delete spec
# ===================================================================

class TestDeleteSpec:
    @pytest.mark.asyncio
    async def test_delete_spec(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/explorer/specs/{spec_id}")
        assert resp.status_code == 200
        # Verify gone
        get_resp = await client.get(f"/api/explorer/specs/{spec_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_spec_cascades_fields(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        await client.post(f"/api/explorer/specs/{spec_id}/fields", json={
            "name": "temp", "offset": 0, "length": 2, "field_type": "uint16",
        })
        resp = await client.delete(f"/api/explorer/specs/{spec_id}")
        assert resp.status_code == 200


# ===================================================================
# POST /api/explorer/specs/{spec_id}/fields — add field
# ===================================================================

class TestAddField:
    @pytest.mark.asyncio
    async def test_add_field(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.post(f"/api/explorer/specs/{spec_id}/fields", json={
            "name": "temperature",
            "offset": 0,
            "length": 2,
            "field_type": "uint16",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "temperature"
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_add_field_to_missing_spec(self, client):
        resp = await client.post("/api/explorer/specs/9999/fields", json={
            "name": "temp", "offset": 0, "length": 2, "field_type": "uint16",
        })
        assert resp.status_code == 404


# ===================================================================
# PUT /api/explorer/specs/{spec_id}/fields/{field_id} — update field
# ===================================================================

class TestUpdateField:
    @pytest.mark.asyncio
    async def test_update_field(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        field_resp = await client.post(f"/api/explorer/specs/{spec_id}/fields", json={
            "name": "temp", "offset": 0, "length": 2, "field_type": "uint16",
        })
        field_id = field_resp.json()["id"]
        resp = await client.put(f"/api/explorer/specs/{spec_id}/fields/{field_id}", json={
            "name": "temperature",
            "endian": "BE",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "temperature"
        assert resp.json()["endian"] == "BE"

    @pytest.mark.asyncio
    async def test_update_field_not_found(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.put(f"/api/explorer/specs/{spec_id}/fields/9999", json={"name": "nope"})
        assert resp.status_code == 404


# ===================================================================
# DELETE /api/explorer/specs/{spec_id}/fields/{field_id} — delete field
# ===================================================================

class TestDeleteField:
    @pytest.mark.asyncio
    async def test_delete_field(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        field_resp = await client.post(f"/api/explorer/specs/{spec_id}/fields", json={
            "name": "temp", "offset": 0, "length": 2, "field_type": "uint16",
        })
        field_id = field_resp.json()["id"]
        resp = await client.delete(f"/api/explorer/specs/{spec_id}/fields/{field_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_field_not_found(self, client):
        create_resp = await client.post("/api/explorer/specs", json={"name": "proto1"})
        spec_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/explorer/specs/{spec_id}/fields/9999")
        assert resp.status_code == 404


# ===================================================================
# GET /api/explorer/ad/{ad_id}/specs — matching specs for an ad
# ===================================================================

class TestMatchingSpecs:
    @pytest.mark.asyncio
    async def test_matching_specs_for_ad(self, client, raw_storage):
        # Create a spec matching Apple company_id=76
        await client.post("/api/explorer/specs", json={
            "name": "apple_proto", "company_id": 76,
        })
        # Insert an Apple ad
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ad/1/specs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["name"] == "apple_proto"

    @pytest.mark.asyncio
    async def test_matching_specs_empty(self, client, raw_storage):
        ad = _make_ad("AA:BB:CC:DD:EE:01", manufacturer_data=b"\x4c\x00\x10\x05")
        await raw_storage.save(ad)
        resp = await client.get("/api/explorer/ad/1/specs")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_matching_specs_ad_not_found(self, client):
        resp = await client.get("/api/explorer/ad/9999/specs")
        assert resp.status_code == 404


# ===================================================================
# GET /api/explorer/specs/{spec_id}/codegen — generate parser code
# ===================================================================

class TestCodegen:
    @pytest.mark.asyncio
    async def test_codegen_returns_python(self, client):
        create_resp = await client.post("/api/explorer/specs", json={
            "name": "my_protocol", "company_id": 76, "data_source": "mfr",
        })
        spec_id = create_resp.json()["id"]
        await client.post(f"/api/explorer/specs/{spec_id}/fields", json={
            "name": "temperature", "offset": 0, "length": 2, "field_type": "uint16",
        })
        resp = await client.get(f"/api/explorer/specs/{spec_id}/codegen")
        assert resp.status_code == 200
        data = resp.json()
        assert "code" in data
        assert "register_parser" in data["code"]

    @pytest.mark.asyncio
    async def test_codegen_not_found(self, client):
        resp = await client.get("/api/explorer/specs/9999/codegen")
        assert resp.status_code == 404


# ===================================================================
# POST /api/explorer/specs with inline fields
# ===================================================================

class TestCreateSpecWithFields:
    """Creating a spec with fields in a single POST should store the fields."""

    @pytest.mark.asyncio
    async def test_create_spec_with_inline_fields(self, client):
        resp = await client.post("/api/explorer/specs", json={
            "name": "my_proto",
            "company_id": 76,
            "fields": [
                {"name": "flags", "offset": 0, "length": 1, "field_type": "uint8"},
                {"name": "temperature", "offset": 1, "length": 2, "field_type": "uint16", "endian": "LE"},
            ],
        })
        assert resp.status_code == 200
        spec_id = resp.json()["id"]

        # Fields should be stored
        get_resp = await client.get(f"/api/explorer/specs/{spec_id}")
        fields = get_resp.json()["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "flags"
        assert fields[1]["name"] == "temperature"

    @pytest.mark.asyncio
    async def test_create_spec_with_fields_codegen_includes_fields(self, client):
        """End-to-end: create spec with fields, codegen should include field extraction."""
        resp = await client.post("/api/explorer/specs", json={
            "name": "test_proto",
            "company_id": 99,
            "fields": [
                {"name": "device_name", "offset": 2, "length": 8, "field_type": "utf8"},
            ],
        })
        spec_id = resp.json()["id"]
        codegen_resp = await client.get(f"/api/explorer/specs/{spec_id}/codegen")
        code = codegen_resp.json()["code"]
        assert "device_name" in code
        assert "decode" in code  # utf8 uses .decode()

    @pytest.mark.asyncio
    async def test_update_spec_replaces_fields(self, client):
        """PUT with fields should replace existing fields."""
        create_resp = await client.post("/api/explorer/specs", json={
            "name": "updatable",
            "company_id": 76,
            "fields": [
                {"name": "old_field", "offset": 0, "length": 1, "field_type": "uint8"},
            ],
        })
        spec_id = create_resp.json()["id"]

        # Update with new fields
        await client.put(f"/api/explorer/specs/{spec_id}", json={
            "fields": [
                {"name": "new_field_a", "offset": 0, "length": 2, "field_type": "uint16"},
                {"name": "new_field_b", "offset": 2, "length": 4, "field_type": "float32"},
            ],
        })

        get_resp = await client.get(f"/api/explorer/specs/{spec_id}")
        fields = get_resp.json()["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "new_field_a"
        assert fields[1]["name"] == "new_field_b"
