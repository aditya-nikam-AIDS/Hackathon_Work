import json
import re
from dataclasses import dataclass, field
from typing import Any

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


@dataclass
class LLMActionPlan:
    requires_human_review: bool = False
    recommended_actions: list[str] = field(default_factory=list)
    escalation_summary: str = ""
    confidence: float = 0.0


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._chat_model = None

    @property
    def enabled(self) -> bool:
        return self.settings.llm_provider != "disabled" and self.settings.use_llm_classifier

    async def analyze_complaint(self, text: str) -> LLMAnalysis | None:
        if not self.enabled:
            return None

        system_prompt = (
            "You classify customer complaints for a support routing system. "
            "Return only valid JSON with keys: category, sentiment_score, "
            "urgency_signals, confidence, reason. category must be one of "
            f"{sorted(ALLOWED_CATEGORIES)}. sentiment_score is -1 to 1."
        )

        try:
            data = await self._invoke_json(system_prompt, text)
            return self._parse_analysis(data)
        except Exception:
            return None

    async def generate_action_plan(
        self,
        *,
        complaint_text: str,
        category: str,
        priority: str,
        team: str,
        sla_deadline: str,
    ) -> LLMActionPlan | None:
        if not self.enabled:
            return None

        system_prompt = (
            "You are an agentic support triage supervisor. "
            "Create an operational action plan for a newly routed customer complaint. "
            "Return only valid JSON with keys: requires_human_review, recommended_actions, "
            "escalation_summary, confidence. recommended_actions must be a list of short actions."
        )
        user_prompt = json.dumps(
            {
                "complaint_text": complaint_text,
                "category": category,
                "priority": priority,
                "team": team,
                "sla_deadline": sla_deadline,
            }
        )

        try:
            data = await self._invoke_json(system_prompt, user_prompt)
            actions = data.get("recommended_actions", [])
            if not isinstance(actions, list):
                actions = [str(actions)]
            return LLMActionPlan(
                requires_human_review=bool(data.get("requires_human_review", False)),
                recommended_actions=[str(action) for action in actions[:5]],
                escalation_summary=str(data.get("escalation_summary", "")),
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
            )
        except Exception:
            return None

    async def _invoke_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = await self._get_chat_model().ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return self._extract_json(self._content_to_text(response.content))

    def _get_chat_model(self):
        if self._chat_model is not None:
            return self._chat_model

        if self.settings.llm_provider == "ollama":
            from langchain_ollama import ChatOllama

            self._chat_model = ChatOllama(
                model=self.settings.llm_model,
                base_url=self.settings.llm_api_base_url,
                temperature=0,
                format="json",
                timeout=self.settings.llm_timeout_seconds,
            )
            return self._chat_model

        from langchain_openai import ChatOpenAI

        self._chat_model = ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_api_base_url,
            api_key=self.settings.llm_api_key,
            temperature=0,
            timeout=self.settings.llm_timeout_seconds,
        )
        return self._chat_model

    def _parse_analysis(self, content: str | dict[str, Any]) -> LLMAnalysis:
        data = content if isinstance(content, dict) else self._extract_json(content)
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

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    def _extract_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))
