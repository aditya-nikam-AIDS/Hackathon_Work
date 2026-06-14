from dataclasses import dataclass, field

from backend.app.services.nlp.preprocessor import clean_text


CRITICAL_KEYWORDS = {
    "account hacked",
    "data breach",
    "fraud",
    "lawsuit",
    "legal action",
    "phishing",
    "security incident",
    "stolen",
    "unauthorized",
}

HIGH_KEYWORDS = {
    "angry",
    "cancel",
    "chargeback",
    "charged twice",
    "escalate",
    "manager",
    "never arrived",
    "outage",
    "refund now",
    "urgent",
}

MEDIUM_KEYWORDS = {
    "broken",
    "damaged",
    "delay",
    "incorrect",
    "late",
    "missing",
    "not working",
    "refund",
}

CUSTOMER_TIER_WEIGHT = {
    "vip": 1.5,
    "premium": 0.75,
    "standard": 0.0,
    "trial": 0.0,
}

CATEGORY_WEIGHT = {
    "fraud_security": 2.0,
    "billing": 0.75,
    "technical": 0.75,
    "refund": 0.5,
    "delivery": 0.5,
    "product_quality": 0.5,
    "account": 0.25,
    "general": 0.0,
}


@dataclass
class PriorityDecision:
    priority: str
    score: float
    reason: str
    signals: list[str] = field(default_factory=list)


class PriorityEngine:
    def decide(
        self,
        *,
        text: str,
        category: str,
        sentiment_score: float,
        customer_tier: str,
    ) -> PriorityDecision:
        cleaned = clean_text(text)
        score = 0.0
        signals: list[str] = []

        critical_hits = [keyword for keyword in CRITICAL_KEYWORDS if keyword in cleaned]
        high_hits = [keyword for keyword in HIGH_KEYWORDS if keyword in cleaned]
        medium_hits = [keyword for keyword in MEDIUM_KEYWORDS if keyword in cleaned]

        if critical_hits:
            score += 3.0
            signals.append(f"critical_keywords={','.join(critical_hits)}")
        if high_hits:
            score += 2.0
            signals.append(f"high_keywords={','.join(high_hits)}")
        if medium_hits:
            score += 1.0
            signals.append(f"medium_keywords={','.join(medium_hits)}")

        if sentiment_score <= -0.65:
            score += 2.0
            signals.append("very_negative_sentiment")
        elif sentiment_score <= -0.30:
            score += 1.0
            signals.append("negative_sentiment")

        tier_weight = CUSTOMER_TIER_WEIGHT.get(customer_tier, 0.0)
        if tier_weight:
            score += tier_weight
            signals.append(f"customer_tier={customer_tier}")

        category_weight = CATEGORY_WEIGHT.get(category, 0.0)
        if category_weight:
            score += category_weight
            signals.append(f"category={category}")

        if score >= 4.5:
            priority = "critical"
        elif score >= 2.75:
            priority = "high"
        elif score >= 1.0:
            priority = "medium"
        else:
            priority = "low"

        reason = "; ".join(signals) if signals else "No high-risk signals detected."
        return PriorityDecision(priority=priority, score=round(score, 2), reason=reason, signals=signals)

