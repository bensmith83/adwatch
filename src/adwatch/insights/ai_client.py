"""AI API client for generating BLE scan insights."""

import json
from dataclasses import dataclass

import httpx

SYSTEM_PROMPT = """\
You are a BLE (Bluetooth Low Energy) advertisement analyst. You're reviewing \
aggregated scan data from a passive BLE scanner.

Analyze the data and provide insights in these categories:

1. **Environment Profile** — What kind of space is this? (home, office, school, public)
2. **Device Clusters** — Groups of related devices and what they suggest
3. **Notable Devices** — Anything unusual, security-relevant, or interesting
4. **Coverage Gaps** — Unparsed devices that might benefit from new parsers
5. **Trends** — Changes in device presence over time, transient vs permanent devices

Keep the analysis concise but insightful. Use markdown formatting.
Identity hashes are anonymized — they distinguish unique devices without revealing MAC addresses.
Do not speculate about specific people or locations beyond what the device data shows.\
"""

DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
}


@dataclass
class InsightResult:
    text: str
    model: str
    token_count: int


class InsightsClient:
    def __init__(self, api_key: str, provider: str = "claude", model: str | None = None):
        self.api_key = api_key
        self.provider = provider
        self.model = model or DEFAULT_MODELS.get(provider, "claude-sonnet-4-20250514")

    async def generate(self, summary: dict) -> InsightResult:
        user_message = (
            "Here is the aggregated BLE scan data to analyze:\n\n"
            f"```json\n{json.dumps(summary, indent=2, default=str)}\n```"
        )

        if self.provider == "openai":
            return await self._call_openai(user_message)
        return await self._call_claude(user_message)

    async def _call_claude(self, user_message: str) -> InsightResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            response.raise_for_status()
            data = response.json()

            text = data["content"][0]["text"]
            model = data.get("model", self.model)
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            return InsightResult(text=text, model=model, token_count=tokens)

    async def _call_openai(self, user_message: str) -> InsightResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 2048,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()

            text = data["choices"][0]["message"]["content"]
            model = data.get("model", self.model)
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return InsightResult(text=text, model=model, token_count=tokens)
