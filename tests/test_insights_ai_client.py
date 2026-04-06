"""Tests for InsightsClient (AI API integration)."""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adwatch.insights.ai_client import InsightsClient, InsightResult, SYSTEM_PROMPT


SAMPLE_SUMMARY = {
    "totals": {"total_ads": 100, "parsed": 60, "unparsed": 40, "parse_rate": 0.6},
    "by_parser": [{"parser": "hatch", "count": 30, "sightings": 5000}],
    "top_devices": [{"identity_hash": "abc123", "local_name": "Test", "sightings": 100}],
}


class TestInsightResult:
    def test_result_fields(self):
        r = InsightResult(text="insight", model="claude-sonnet-4-20250514", token_count=500)
        assert r.text == "insight"
        assert r.model == "claude-sonnet-4-20250514"
        assert r.token_count == 500


class TestInsightsClientInit:
    def test_claude_provider(self):
        client = InsightsClient(api_key="test-key", provider="claude")
        assert client.provider == "claude"

    def test_openai_provider(self):
        client = InsightsClient(api_key="test-key", provider="openai")
        assert client.provider == "openai"

    def test_default_model_claude(self):
        client = InsightsClient(api_key="test-key", provider="claude")
        assert "claude" in client.model

    def test_default_model_openai(self):
        client = InsightsClient(api_key="test-key", provider="openai")
        assert "gpt" in client.model

    def test_custom_model(self):
        client = InsightsClient(api_key="test-key", provider="claude", model="custom-model")
        assert client.model == "custom-model"


class TestInsightsClientClaude:
    @pytest.fixture
    def client(self):
        return InsightsClient(api_key="test-key", provider="claude")

    async def test_generate_claude_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "## Environment Profile\nThis looks like a home."}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 300, "output_tokens": 200},
        }

        with patch("adwatch.insights.ai_client.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.generate(SAMPLE_SUMMARY)

        assert isinstance(result, InsightResult)
        assert "Environment Profile" in result.text
        assert result.token_count == 500

    async def test_generate_claude_sends_correct_headers(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "insight"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 100, "output_tokens": 100},
        }

        with patch("adwatch.insights.ai_client.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await client.generate(SAMPLE_SUMMARY)

            call_kwargs = mock_ctx.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            assert "x-api-key" in headers
            assert headers["x-api-key"] == "test-key"
            assert "anthropic-version" in headers

    async def test_generate_claude_error(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))

        with patch("adwatch.insights.ai_client.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(Exception):
                await client.generate(SAMPLE_SUMMARY)


class TestInsightsClientOpenAI:
    @pytest.fixture
    def client(self):
        return InsightsClient(api_key="test-key", provider="openai")

    async def test_generate_openai_success(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "## Analysis\nHome environment."}}],
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 300, "completion_tokens": 200, "total_tokens": 500},
        }

        with patch("adwatch.insights.ai_client.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await client.generate(SAMPLE_SUMMARY)

        assert isinstance(result, InsightResult)
        assert "Analysis" in result.text
        assert result.token_count == 500


class TestSystemPrompt:
    def test_system_prompt_exists(self):
        assert len(SYSTEM_PROMPT) > 100
        assert "BLE" in SYSTEM_PROMPT
