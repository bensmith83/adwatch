"""Tests for the Pipeline class — red phase."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from adwatch.models import RawAdvertisement, Classification, ParseResult
from adwatch.pipeline import Pipeline


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
def classification():
    return Classification(ad_type="apple_nearby", ad_category="phone", source="company_id")


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


@pytest.fixture
def parse_result_event_only():
    return ParseResult(
        parser_name="event_parser",
        beacon_type="event_test",
        device_class="phone",
        identifier_hash="1234567890abcdef",
        raw_payload_hex="aabbcc",
        metadata={"action": "nearby"},
        event_type="event_test_sighting",
        storage_table=None,
        storage_row=None,
    )


@pytest.fixture
def deps():
    return {
        "raw_storage": AsyncMock(),
        "classifier": MagicMock(),
        "registry": MagicMock(),
        "websocket_emitter": AsyncMock(),
    }


@pytest.fixture
def pipeline(deps):
    return Pipeline(
        raw_storage=deps["raw_storage"],
        classifier=deps["classifier"],
        registry=deps["registry"],
        websocket_emitter=deps["websocket_emitter"],
    )


class TestPipelineInit:
    def test_pipeline_accepts_dependencies(self, deps):
        p = Pipeline(
            raw_storage=deps["raw_storage"],
            classifier=deps["classifier"],
            registry=deps["registry"],
            websocket_emitter=deps["websocket_emitter"],
        )
        assert p is not None


class TestPipelineProcess:
    @pytest.mark.asyncio
    async def test_always_saves_raw_ad(self, pipeline, deps, raw_ad):
        deps["classifier"].classify.return_value = None
        deps["registry"].match.return_value = []

        await pipeline.process(raw_ad)

        deps["raw_storage"].save.assert_called_once()
        call_args = deps["raw_storage"].save.call_args
        assert call_args[0][0] is raw_ad or call_args.kwargs.get("raw") is raw_ad or raw_ad in call_args[0]

    @pytest.mark.asyncio
    async def test_classifies_the_ad(self, pipeline, deps, raw_ad, classification):
        deps["classifier"].classify.return_value = classification
        deps["registry"].match.return_value = []

        await pipeline.process(raw_ad)

        deps["classifier"].classify.assert_called_once_with(raw_ad)

    @pytest.mark.asyncio
    async def test_routes_to_matching_parsers(self, pipeline, deps, raw_ad):
        deps["classifier"].classify.return_value = None
        mock_parser = MagicMock()
        mock_parser.parse.return_value = None
        deps["registry"].match.return_value = [mock_parser]

        await pipeline.process(raw_ad)

        deps["registry"].match.assert_called_once_with(raw_ad)
        mock_parser.parse.assert_called_once_with(raw_ad)

    @pytest.mark.asyncio
    async def test_no_matching_parsers(self, pipeline, deps, raw_ad):
        deps["classifier"].classify.return_value = None
        deps["registry"].match.return_value = []

        await pipeline.process(raw_ad)

        # Should still save and emit sighting even with no parsers
        deps["raw_storage"].save.assert_called_once()
        # Should emit the generic "sighting" event
        deps["websocket_emitter"].emit.assert_called_once()
        call_args = deps["websocket_emitter"].emit.call_args
        assert call_args[0][0] == "sighting"

    @pytest.mark.asyncio
    async def test_parser_returns_none_skipped(self, pipeline, deps, raw_ad):
        deps["classifier"].classify.return_value = None
        mock_parser = MagicMock()
        mock_parser.parse.return_value = None
        deps["registry"].match.return_value = [mock_parser]

        await pipeline.process(raw_ad)

        # Only the generic sighting event, no parser-specific events
        assert deps["websocket_emitter"].emit.call_count == 1
        assert deps["websocket_emitter"].emit.call_args[0][0] == "sighting"

    @pytest.mark.asyncio
    async def test_parser_with_storage(self, pipeline, deps, raw_ad, parse_result_with_storage):
        deps["classifier"].classify.return_value = None
        mock_parser = MagicMock()
        mock_parser.parse.return_value = parse_result_with_storage
        deps["registry"].match.return_value = [mock_parser]

        await pipeline.process(raw_ad)

        # Should store parsed data
        # Look for a call that saves to the storage_table
        emit_calls = deps["websocket_emitter"].emit.call_args_list
        event_types = [c[0][0] for c in emit_calls]
        assert "test_reading" in event_types
        assert "sighting" in event_types

    @pytest.mark.asyncio
    async def test_parser_with_event(self, pipeline, deps, raw_ad, parse_result_event_only):
        deps["classifier"].classify.return_value = None
        mock_parser = MagicMock()
        mock_parser.parse.return_value = parse_result_event_only
        deps["registry"].match.return_value = [mock_parser]

        await pipeline.process(raw_ad)

        emit_calls = deps["websocket_emitter"].emit.call_args_list
        event_types = [c[0][0] for c in emit_calls]
        assert "event_test_sighting" in event_types
        assert "sighting" in event_types

    @pytest.mark.asyncio
    async def test_classification_none_for_unknown(self, pipeline, deps):
        unknown = RawAdvertisement(
            timestamp="2025-01-15T10:30:00+00:00",
            mac_address="00:11:22:33:44:55",
            address_type="public",
            manufacturer_data=b"\xFF\xFF\x01\x02\x03",
            service_data=None,
            service_uuids=[],
            local_name=None,
            rssi=-80,
            tx_power=None,
        )
        deps["classifier"].classify.return_value = None
        deps["registry"].match.return_value = []

        await pipeline.process(unknown)

        # Sighting event should include None classification
        sighting_call = deps["websocket_emitter"].emit.call_args
        assert sighting_call[0][0] == "sighting"
        payload = sighting_call[0][1]
        assert payload["classification"] is None

    @pytest.mark.asyncio
    async def test_multiple_matching_parsers(self, pipeline, deps, raw_ad):
        deps["classifier"].classify.return_value = None

        result1 = ParseResult(
            parser_name="parser_a", beacon_type="type_a", device_class="phone",
            identifier_hash="aaaa", raw_payload_hex="aa",
            event_type="event_a", storage_table=None, storage_row=None,
        )
        result2 = ParseResult(
            parser_name="parser_b", beacon_type="type_b", device_class="phone",
            identifier_hash="bbbb", raw_payload_hex="bb",
            event_type="event_b", storage_table=None, storage_row=None,
        )
        parser_a = MagicMock()
        parser_a.parse.return_value = result1
        parser_b = MagicMock()
        parser_b.parse.return_value = result2
        deps["registry"].match.return_value = [parser_a, parser_b]

        await pipeline.process(raw_ad)

        parser_a.parse.assert_called_once_with(raw_ad)
        parser_b.parse.assert_called_once_with(raw_ad)
        emit_calls = deps["websocket_emitter"].emit.call_args_list
        event_types = [c[0][0] for c in emit_calls]
        assert "event_a" in event_types
        assert "event_b" in event_types
        assert "sighting" in event_types

    @pytest.mark.asyncio
    async def test_sighting_event_includes_raw_and_classification(
        self, pipeline, deps, raw_ad, classification
    ):
        deps["classifier"].classify.return_value = classification
        deps["registry"].match.return_value = []

        await pipeline.process(raw_ad)

        sighting_call = deps["websocket_emitter"].emit.call_args
        assert sighting_call[0][0] == "sighting"
        payload = sighting_call[0][1]
        assert payload["raw"] is raw_ad
        assert payload["classification"] is classification
