from dataclasses import dataclass
from typing import Literal
from pathlib import Path

import joblib

from backend.app.core.config import Settings
from backend.app.services.nlp.llm_client import LLMAnalysis, LLMClient
from backend.app.services.nlp.preprocessor import clean_text
from backend.app.services.nlp.sentiment import score_sentiment


# Banking domain category keywords
CATEGORY_KEYWORDS = {
    "transaction_issue": {
        "transaction failed",
        "payment failed",
        "money deducted",
        "amount debited",
        "not received",
        "upi failed",
        "neft pending",
        "imps failed",
        "rtgs issue",
        "transfer stuck",
        "payment delay",
        "double debit",
        "charged twice",
        "refund pending",
        "reversal",
        "beneficiary",
        "wrong account",
    },
    "account_issue": {
        "account blocked",
        "account frozen",
        "cannot login",
        "login failed",
        "password issue",
        "otp not received",
        "kyc pending",
        "kyc rejected",
        "account update",
        "profile change",
        "address update",
        "nominee update",
        "account closure",
        "dormant account",
        "inactive account",
        "joint account",
    },
    "fraud_security": {
        "fraud",
        "unauthorized",
        "hacked",
        "phishing",
        "scam",
        "suspicious",
        "stolen",
        "card cloned",
        "otp misuse",
        "identity theft",
        "unknown transaction",
        "did not authorize",
        "security breach",
        "data breach",
        "compromised",
    },
    "loan_credit_issue": {
        "loan",
        "emi",
        "credit card",
        "credit limit",
        "loan rejected",
        "loan approval",
        "interest rate",
        "prepayment",
        "foreclosure",
        "loan statement",
        "credit score",
        "cibil",
        "personal loan",
        "home loan",
        "car loan",
        "overdue",
        "late fee",
        "billing dispute",
    },
    "technical_issue": {
        "app crash",
        "app not working",
        "website error",
        "server error",
        "page not loading",
        "system down",
        "outage",
        "mobile banking",
        "net banking",
        "internet banking",
        "slow",
        "timeout",
        "session expired",
        "bug",
        "glitch",
    },
}


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    source: str
    sentiment_score: float
    model_reason: str = ""


ClassificationMode = Literal["auto", "llm", "tfidf"]


class ComplaintClassifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_client = LLMClient(settings)
        self.model = self._load_model(settings.model_path)

    async def classify(self, text: str, mode: ClassificationMode = "auto") -> ClassificationResult:
        llm_analysis = None
        if mode in {"auto", "llm"}:
            llm_analysis = await self.llm_client.analyze_complaint(text)
            if llm_analysis and llm_analysis.confidence >= 0.55:
                return self._from_llm(llm_analysis, text)

        ml_result = self._classify_with_trained_model(text)
        if ml_result:
            if mode == "tfidf":
                ml_result.model_reason = "TF-IDF classifier selected by agent."
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
