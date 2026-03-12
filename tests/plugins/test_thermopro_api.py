"""Tests for ThermoPro API router."""

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from adwatch.plugins.thermopro import ThermoProParser
from adwatch.storage.base import Database


@pytest.fixture
async def db(tmp_path):
    database = Database()
    await database.connect(str(tmp_path / "test.db"))
    await database.execute("""CREATE TABLE IF NOT EXISTS thermopro_sightings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        mac_address TEXT NOT NULL,
        sensor_id TEXT NOT NULL,
        model_code TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        humidity INTEGER NOT NULL,
        room_speculation TEXT NOT NULL,
        identifier_hash TEXT NOT NULL,
        rssi INTEGER,
        raw_payload_hex TEXT
    )""")
    yield database
    await database.close()


@pytest.fixture
async def client(db):
    parser = ThermoProParser()
    router = parser.api_router(db)
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestThermoProAPI:
    @pytest.mark.asyncio
    async def test_active_empty(self, client):
        resp = await client.get("/active")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_active_returns_latest_per_sensor(self, client, db):
        # Insert two readings for same sensor, one old one new
        await db.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2025-01-15T10:00:00", "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 20.0, 45, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )
        await db.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2025-01-15T10:30:00", "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -42, "ccdd"),
        )
        # Different sensor
        await db.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2025-01-15T10:15:00", "AA:BB:CC:DD:EE:FF", "TP393 (1A2B)",
             "TP393", -18.5, 30, "Freezer", "def456", -60, "eeff"),
        )

        resp = await client.get("/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        # Should be latest reading per sensor
        by_sensor = {d["sensor_id"]: d for d in data}
        assert by_sensor["TP357 (2B54)"]["temperature_c"] == 21.5
        assert by_sensor["TP393 (1A2B)"]["temperature_c"] == -18.5


# --- Nickname tests ---


@pytest.fixture
async def db_with_nicknames(tmp_path):
    """Database with both sightings and nicknames tables."""
    database = Database()
    await database.connect(str(tmp_path / "test_nick.db"))
    await database.execute("""CREATE TABLE IF NOT EXISTS thermopro_sightings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        mac_address TEXT NOT NULL,
        sensor_id TEXT NOT NULL,
        model_code TEXT NOT NULL,
        temperature_c REAL NOT NULL,
        humidity INTEGER NOT NULL,
        room_speculation TEXT NOT NULL,
        identifier_hash TEXT NOT NULL,
        rssi INTEGER,
        raw_payload_hex TEXT
    )""")
    await database.execute("""CREATE TABLE IF NOT EXISTS thermopro_nicknames (
        sensor_id TEXT PRIMARY KEY,
        nickname TEXT NOT NULL
    )""")
    yield database
    await database.close()


@pytest.fixture
async def nick_client(db_with_nicknames):
    parser = ThermoProParser()
    router = parser.api_router(db_with_nicknames)
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestThermoProNicknameAPI:
    @pytest.mark.asyncio
    async def test_put_nickname_creates_entry(self, nick_client, db_with_nicknames):
        """PUT /nickname should store a nickname for a sensor."""
        resp = await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)", "nickname": "Living Room"},
        )
        assert resp.status_code == 200

        row = await db_with_nicknames.fetchone(
            "SELECT nickname FROM thermopro_nicknames WHERE sensor_id = ?",
            ("TP357 (2B54)",),
        )
        assert row is not None
        assert row["nickname"] == "Living Room"

    @pytest.mark.asyncio
    async def test_put_nickname_updates_existing(self, nick_client, db_with_nicknames):
        """PUT /nickname should update an existing nickname."""
        await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)", "nickname": "Living Room"},
        )
        await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)", "nickname": "Bedroom"},
        )

        row = await db_with_nicknames.fetchone(
            "SELECT nickname FROM thermopro_nicknames WHERE sensor_id = ?",
            ("TP357 (2B54)",),
        )
        assert row["nickname"] == "Bedroom"

    @pytest.mark.asyncio
    async def test_put_nickname_returns_200_with_body(self, nick_client):
        """PUT /nickname should return 200 with confirmation."""
        resp = await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)", "nickname": "Kitchen"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["sensor_id"] == "TP357 (2B54)"
        assert body["nickname"] == "Kitchen"

    @pytest.mark.asyncio
    async def test_put_nickname_missing_sensor_id_returns_422(self, nick_client):
        """PUT /nickname with missing sensor_id should return 422."""
        resp = await nick_client.put(
            "/nickname",
            json={"nickname": "Kitchen"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_put_nickname_missing_nickname_returns_422(self, nick_client):
        """PUT /nickname with missing nickname should return 422."""
        resp = await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_put_nickname_empty_body_returns_422(self, nick_client):
        """PUT /nickname with empty body should return 422."""
        resp = await nick_client.put("/nickname", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_active_includes_nickname_field(self, nick_client, db_with_nicknames):
        """GET /active should include nickname (null if unset)."""
        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2025-01-15T10:00:00", "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )

        resp = await nick_client.get("/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert "nickname" in data[0]
        assert data[0]["nickname"] is None

    @pytest.mark.asyncio
    async def test_active_includes_set_nickname(self, nick_client, db_with_nicknames):
        """GET /active should return the nickname when one is set."""
        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("2025-01-15T10:00:00", "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )
        await nick_client.put(
            "/nickname",
            json={"sensor_id": "TP357 (2B54)", "nickname": "Garage"},
        )

        resp = await nick_client.get("/active")
        data = resp.json()
        assert data[0]["nickname"] == "Garage"


# --- timeout_minutes tests ---


class TestThermoProActiveTimeout:
    @pytest.mark.asyncio
    async def test_timeout_filters_old_sensors(self, nick_client, db_with_nicknames):
        """GET /active?timeout_minutes=5 should only return sensors seen within 5 min."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S")
        old = (now - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")

        # Insert a recent sensor
        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (recent, "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )
        # Insert an old sensor
        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (old, "AA:BB:CC:DD:EE:FF", "TP393 (1A2B)",
             "TP393", -18.5, 30, "Freezer", "def456", -60, "eeff"),
        )

        resp = await nick_client.get("/active?timeout_minutes=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["sensor_id"] == "TP357 (2B54)"

    @pytest.mark.asyncio
    async def test_no_timeout_returns_all(self, nick_client, db_with_nicknames):
        """GET /active without timeout_minutes should return all sensors."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        recent = (now - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S")
        old = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (recent, "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )
        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (old, "AA:BB:CC:DD:EE:FF", "TP393 (1A2B)",
             "TP393", -18.5, 30, "Freezer", "def456", -60, "eeff"),
        )

        resp = await nick_client.get("/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_timeout_zero_returns_all(self, nick_client, db_with_nicknames):
        """GET /active?timeout_minutes=0 should return all sensors (no filtering)."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        old = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (old, "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )

        resp = await nick_client.get("/active?timeout_minutes=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_timeout_negative_returns_all(self, nick_client, db_with_nicknames):
        """GET /active?timeout_minutes=-5 should return all sensors (no filtering)."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        old = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")

        await db_with_nicknames.execute(
            """INSERT INTO thermopro_sightings
               (timestamp, mac_address, sensor_id, model_code, temperature_c,
                humidity, room_speculation, identifier_hash, rssi, raw_payload_hex)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (old, "11:22:33:44:55:66", "TP357 (2B54)",
             "TP357", 21.5, 50, "Indoor (comfortable)", "abc123", -45, "aabb"),
        )

        resp = await nick_client.get("/active?timeout_minutes=-5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
