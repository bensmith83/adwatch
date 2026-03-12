"""Tests for pipeline storing parsed data to plugin tables."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.pipeline import Pipeline
from adwatch.storage.base import Database
from adwatch.storage.migrations import run_migrations


@pytest.fixture
def raw_ad():
    return RawAdvertisement(
        timestamp="2025-01-15T10:30:00+00:00",
        mac_address="AA:BB:CC:DD:EE:FF",
        address_type="random",
        manufacturer_data=b"\x4c\x00\x10\x05\x01",
        service_data=None,
        service_uuids=[],
        local_name=None,
        rssi=-62,
        tx_power=None,
    )


@pytest.fixture
def parse_result_with_storage():
    return ParseResult(
        parser_name="test_parser",
        beacon_type="test",
        device_class="sensor",
        identifier_hash="abcdef0123456789",
        raw_payload_hex="0102030405",
        metadata={"temp": 22.5},
        event_type="test_reading",
        storage_table="test_sightings",
        storage_row={"temp": 22.5, "mac": "AA:BB:CC:DD:EE:FF"},
    )


class TestPipelineStoresParsedData:
    @pytest.mark.asyncio
    async def test_stores_to_plugin_table(self, tmp_path, raw_ad, parse_result_with_storage):
        db = Database()
        await db.connect(str(tmp_path / "test.db"))
        await db.execute(
            "CREATE TABLE test_sightings (temp REAL, mac TEXT)"
        )

        raw_storage = AsyncMock()
        classifier = MagicMock()
        classifier.classify.return_value = None
        registry = MagicMock()
        mock_parser = MagicMock()
        mock_parser.parse.return_value = parse_result_with_storage
        registry.match.return_value = [mock_parser]

        pipeline = Pipeline(raw_storage, classifier, registry, db=db)
        await pipeline.process(raw_ad)

        rows = await db.fetchall("SELECT * FROM test_sightings")
        assert len(rows) == 1
        assert rows[0]["temp"] == 22.5
        assert rows[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        await db.close()

    @pytest.mark.asyncio
    async def test_skips_storage_when_no_table(self, raw_ad):
        """ParseResult with no storage_table should not attempt insert."""
        result = ParseResult(
            parser_name="event_only",
            beacon_type="test",
            device_class="phone",
            identifier_hash="1234",
            raw_payload_hex="aa",
            event_type="ev",
            storage_table=None,
            storage_row=None,
        )
        raw_storage = AsyncMock()
        classifier = MagicMock()
        classifier.classify.return_value = None
        registry = MagicMock()
        mock_parser = MagicMock()
        mock_parser.parse.return_value = result
        registry.match.return_value = [mock_parser]

        db = MagicMock()
        pipeline = Pipeline(raw_storage, classifier, registry, db=db)
        await pipeline.process(raw_ad)

        db.execute.assert_not_called()
