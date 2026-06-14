from dataclasses import dataclass
from pathlib import Path

import joblib

from backend.app.core.config import Settings
from backend.app.services.nlp.llm_client import LLMAnalysis, LLMClient
from backend.app.services.nlp.preprocessor import clean_text
from backend.app.services.nlp.sentiment import score_sentiment


CATEGORY_KEYWORDS = {
    "billing": {
        "invoice",
        "charged",
        "charge",
        "payment",
        "bill",
        "billing",
        "subscription",
        "price",
        "overcharged",
    },
    "technical": {
        "app",
        "bug",
        "crash",
        "error",
        "login",
        "otp",
        "outage",
        "password",
        "server",
        "website",
        "not working",
    },
    "delivery": {
        "courier",
        "delayed",
        "delivery",
        "package",
        "parcel",
        "shipment",
        "tracking",
        "warehouse",
        "never arrived",
    },
    "product_quality": {
        "broken",
        "damaged",
        "defective",
        "faulty",
        "quality",
        "scratch",
        "spoiled",
        "missing part",
    },
    "account": {
        "address",
        "account",
        "cancel",
        "profile",
        "plan",
        "kyc",
        "upgrade",
        "delete my account",
    },
    "fraud_security": {
        "fraud",
        "hacked",
        "phishing",
        "scam",
        "security",
        "stolen",
        "unauthorized",
        "data breach",
    },
    "refund": {
        "refund",
        "return",
        "reversal",
        "money back",
        "credited",
        "chargeback",
    },
}


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    source: str
    sentiment_score: float
    model_reason: str = ""


class ComplaintClassifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_client = LLMClient(settings)
        self.model = self._load_model(settings.model_path)

    async def classify(self, text: str) -> ClassificationResult:
        llm_analysis = await self.llm_client.analyze_complaint(text)
        if llm_analysis and llm_analysis.confidence >= 0.55:
            return self._from_llm(llm_analysis, text)

        ml_result = self._classify_with_trained_model(text)
        if ml_result:
            return ml_result

        return self._keyword_fallback(text, llm_analysis)

    def _load_model(self, model_path: str):
        path = Path(model_path)
        if not path.exists():
            return None
        try:
            return joblib.load(path)
        except (OSError, ValueError):
            return None

    def _from_llm(self, analysis: LLMAnalysis, text: str) -> ClassificationResult:
        sentiment = analysis.sentiment_score
        if sentiment == 0:
            sentiment = score_sentiment(text)
        return ClassificationResult(
            category=analysis.category,
            confidence=analysis.confidence,
            source="llm",
            sentiment_score=sentiment,
            model_reason=analysis.reason,
        )

    def _classify_with_trained_model(self, text: str) -> ClassificationResult | None:
        if self.model is None:
            return None
        try:
            predicted = str(self.model.predict([text])[0])
            confidence = 0.70
            if hasattr(self.model, "predict_proba"):
                probabilities = self.model.predict_proba([text])[0]
                confidence = float(max(probabilities))
            return ClassificationResult(
                category=predicted,
                confidence=confidence,
                source="tfidf_model",
                sentiment_score=score_sentiment(text),
                model_reason="Trained TF-IDF classifier prediction.",
            )
        except (ValueError, AttributeError):
            return None

    def _keyword_fallback(self, text: str, llm_analysis: LLMAnalysis | None = None) -> ClassificationResult:
        cleaned = clean_text(text)
        scores: dict[str, int] = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            scores[category] = sum(1 for keyword in keywords if keyword in cleaned)

        category, hits = max(scores.items(), key=lambda item: item[1])
        if hits == 0 and llm_analysis:
            category = llm_analysis.category
        elif hits == 0:
            category = "general"

        confidence = min(0.85, 0.35 + (hits * 0.15)) if hits else 0.35
        return ClassificationResult(
            category=category,
            confidence=confidence,
            source="keyword_fallback",
            sentiment_score=score_sentiment(text),
            model_reason="Keyword fallback used because no confident model result was available.",
        )
