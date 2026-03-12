"""Tests for WebSocket throttling — red phase."""

import asyncio

import pytest
from unittest.mock import AsyncMock

from adwatch.dashboard.websocket import WebSocketManager, ThrottledEmitter


class TestThrottledEmitter:
    """ThrottledEmitter wraps WebSocketManager, buffering sighting events."""

    @pytest.fixture
    def ws_manager(self):
        return AsyncMock(spec=WebSocketManager)

    @pytest.fixture
    def emitter(self, ws_manager):
        return ThrottledEmitter(ws_manager, flush_interval=0.1)

    @pytest.mark.asyncio
    async def test_non_sighting_events_pass_through_immediately(self, emitter, ws_manager):
        """Parser-specific events (thermopro_reading, etc.) are sent immediately."""
        await emitter.emit("thermopro_reading", {"temp": 22.5})
        ws_manager.emit.assert_called_once_with("thermopro_reading", {"temp": 22.5})

    @pytest.mark.asyncio
    async def test_sighting_events_are_buffered(self, emitter, ws_manager):
        """Sighting events are NOT sent immediately — they're buffered."""
        await emitter.emit("sighting", {"raw": "ad1"})
        ws_manager.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_buffered_sightings_flushed_as_batch(self, emitter, ws_manager):
        """After flush interval, buffered sightings are sent as a single batch."""
        await emitter.start()
        try:
            await emitter.emit("sighting", {"raw": "ad1"})
            await emitter.emit("sighting", {"raw": "ad2"})
            await emitter.emit("sighting", {"raw": "ad3"})

            # Nothing sent yet
            ws_manager.emit.assert_not_called()

            # Wait for flush
            await asyncio.sleep(0.15)

            ws_manager.emit.assert_called_once()
            call_args = ws_manager.emit.call_args
            assert call_args[0][0] == "sighting_batch"
            assert len(call_args[0][1]) == 3
            assert call_args[0][1][0] == {"raw": "ad1"}
        finally:
            await emitter.stop()

    @pytest.mark.asyncio
    async def test_no_flush_when_buffer_empty(self, emitter, ws_manager):
        """No message sent if no sightings buffered during interval."""
        await emitter.start()
        try:
            await asyncio.sleep(0.15)
            ws_manager.emit.assert_not_called()
        finally:
            await emitter.stop()

    @pytest.mark.asyncio
    async def test_summary_events_pass_through(self, emitter, ws_manager):
        """Summary events are sent immediately, not buffered."""
        await emitter.emit("summary", {"total": 100})
        ws_manager.emit.assert_called_once_with("summary", {"total": 100})

    @pytest.mark.asyncio
    async def test_buffer_cleared_after_flush(self, emitter, ws_manager):
        """Buffer is emptied after each flush."""
        await emitter.start()
        try:
            await emitter.emit("sighting", {"raw": "ad1"})
            await asyncio.sleep(0.15)

            # First flush
            assert ws_manager.emit.call_count == 1

            # Wait another interval — no second flush since buffer is empty
            ws_manager.emit.reset_mock()
            await asyncio.sleep(0.15)
            ws_manager.emit.assert_not_called()
        finally:
            await emitter.stop()

    @pytest.mark.asyncio
    async def test_stop_flushes_remaining(self, emitter, ws_manager):
        """Stopping the emitter flushes any remaining buffered sightings."""
        await emitter.start()
        await emitter.emit("sighting", {"raw": "ad1"})
        await emitter.stop()

        ws_manager.emit.assert_called_once()
        assert ws_manager.emit.call_args[0][0] == "sighting_batch"

    @pytest.mark.asyncio
    async def test_mixed_events_ordering(self, emitter, ws_manager):
        """Non-sighting events pass through even while sightings are buffered."""
        await emitter.start()
        try:
            await emitter.emit("sighting", {"raw": "ad1"})
            await emitter.emit("thermopro_reading", {"temp": 22.5})
            await emitter.emit("sighting", {"raw": "ad2"})

            # thermopro_reading was sent immediately
            assert ws_manager.emit.call_count == 1
            assert ws_manager.emit.call_args[0][0] == "thermopro_reading"

            # Wait for sighting flush
            await asyncio.sleep(0.15)
            assert ws_manager.emit.call_count == 2
            batch_call = ws_manager.emit.call_args
            assert batch_call[0][0] == "sighting_batch"
            assert len(batch_call[0][1]) == 2
        finally:
            await emitter.stop()

    @pytest.mark.asyncio
    async def test_connect_delegates_to_manager(self, emitter, ws_manager):
        """connect() is delegated to the underlying WebSocketManager."""
        mock_ws = AsyncMock()
        await emitter.connect(mock_ws)
        ws_manager.connect.assert_called_once_with(mock_ws)

    @pytest.mark.asyncio
    async def test_disconnect_delegates_to_manager(self, emitter, ws_manager):
        """disconnect() is delegated to the underlying WebSocketManager."""
        mock_ws = AsyncMock()
        await emitter.disconnect(mock_ws)
        ws_manager.disconnect.assert_called_once_with(mock_ws)
