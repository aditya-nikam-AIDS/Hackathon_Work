import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.app.core.config import Settings


ALLOWED_CATEGORIES = {
    "billing",
    "technical",
    "delivery",
    "product_quality",
    "account",
    "fraud_security",
    "refund",
    "general",
}


@dataclass
class LLMAnalysis:
    category: str = "general"
    sentiment_score: float = 0.0
    urgency_signals: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reason: str = ""


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.llm_provider != "disabled" and self.settings.use_llm_classifier

    async def analyze_complaint(self, text: str) -> LLMAnalysis | None:
        if not self.enabled:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You classify customer complaints for a support routing system. "
                    "Return only valid JSON with keys: category, sentiment_score, "
                    "urgency_signals, confidence, reason. category must be one of "
                    f"{sorted(ALLOWED_CATEGORIES)}. sentiment_score is -1 to 1."
                ),
            },
            {"role": "user", "content": text},
        ]

        try:
            if self.settings.llm_provider == "ollama":
                payload = {
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                }
                url = f"{self.settings.llm_api_base_url.rstrip('/')}/api/chat"
                async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                content = response.json()["message"]["content"]
                return self._parse_analysis(content)

            payload = {
                "model": self.settings.llm_model,
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            headers = {"Content-Type": "application/json"}
            if self.settings.llm_api_key:
                headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

            url = f"{self.settings.llm_api_base_url.rstrip('/')}/chat/completions"
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_analysis(content)
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
            return None

    def _parse_analysis(self, content: str | dict[str, Any]) -> LLMAnalysis:
        data = content if isinstance(content, dict) else json.loads(content)
        category = str(data.get("category", "general")).strip().lower()
        if category not in ALLOWED_CATEGORIES:
            category = "general"

        sentiment_score = float(data.get("sentiment_score", 0.0))
        confidence = float(data.get("confidence", 0.0))
        urgency_signals = data.get("urgency_signals", [])
        if not isinstance(urgency_signals, list):
            urgency_signals = [str(urgency_signals)]

        return LLMAnalysis(
            category=category,
            sentiment_score=max(-1.0, min(1.0, sentiment_score)),
            urgency_signals=[str(signal) for signal in urgency_signals],
            confidence=max(0.0, min(1.0, confidence)),
            reason=str(data.get("reason", "")),
        )

