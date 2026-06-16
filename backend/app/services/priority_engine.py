from dataclasses import dataclass, field

from backend.app.services.nlp.preprocessor import clean_text


# Banking domain critical keywords - immediate action required
CRITICAL_KEYWORDS = {
    "account hacked",
    "unauthorized transaction",
    "fraud",
    "money stolen",
    "phishing",
    "security breach",
    "identity theft",
    "card cloned",
    "suspicious login",
    "otp misuse",
    "system outage",
    "atm swallowed card",
    "large amount missing",
    "account frozen wrongly",
}

# Banking domain high priority keywords
HIGH_KEYWORDS = {
    "payment failed",
    "money deducted not received",
    "transaction stuck",
    "upi failed",
    "neft pending",
    "imps failed",
    "account blocked",
    "login failed",
    "cannot access account",
    "emi not debited",
    "loan rejected wrongly",
    "credit card dispute",
    "urgent",
    "escalate",
    "manager",
}

# Banking domain medium priority keywords
MEDIUM_KEYWORDS = {
    "transaction delay",
    "statement incorrect",
    "wrong debit",
    "kyc pending",
    "account update",
    "beneficiary issue",
    "cheque bounce",
    "interest rate query",
    "emi schedule",
    "credit limit",
    "passbook update",
    "balance mismatch",
}

# Customer tier weights for banking
CUSTOMER_TIER_WEIGHT = {
    "vip": 2.0,        # VIP banking customers get highest priority
    "premium": 1.0,    # Premium account holders
    "standard": 0.0,   # Regular customers
    "trial": 0.0,      # Trial/new customers
}

# Category risk weights for banking
CATEGORY_WEIGHT = {
    "fraud_security": 2.5,      # Highest risk - financial crime
    "transaction_issue": 1.5,   # Money at stake
    "loan_credit_issue": 1.0,   # Credit/loan matters
    "account_issue": 0.75,      # Account access issues
    "technical_issue": 0.5,     # App/system issues
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

