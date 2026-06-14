from math import sqrt

from backend.app.services.nlp.preprocessor import clean_text, tokenize


POSITIVE_WORDS = {
    "thanks",
    "thank",
    "resolved",
    "helpful",
    "good",
    "great",
    "excellent",
    "quick",
    "appreciate",
}

NEGATIVE_WORDS = {
    "angry",
    "bad",
    "broken",
    "cancel",
    "charged",
    "complaint",
    "delay",
    "disappointed",
    "fraud",
    "frustrated",
    "horrible",
    "incorrect",
    "late",
    "lost",
    "missing",
    "never",
    "not",
    "outage",
    "refund",
    "scam",
    "stolen",
    "terrible",
    "unacceptable",
    "unauthorized",
    "urgent",
    "worst",
}

NEGATIVE_PHRASES = {
    "not working",
    "never arrived",
    "charged twice",
    "unauthorized charge",
    "account hacked",
    "data breach",
    "legal action",
    "cancel my account",
}


def score_sentiment(text: str) -> float:
    cleaned = clean_text(text)
    tokens = tokenize(cleaned)
    if not tokens:
        return 0.0

    positive_hits = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative_hits = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    phrase_penalty = sum(1 for phrase in NEGATIVE_PHRASES if phrase in cleaned)

    raw = positive_hits - negative_hits - (phrase_penalty * 1.5)
    normalized = raw / max(3.0, sqrt(len(tokens)))
    return max(-1.0, min(1.0, normalized))

