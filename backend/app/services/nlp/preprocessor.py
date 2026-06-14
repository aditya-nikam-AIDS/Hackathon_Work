import re


WHITESPACE_RE = re.compile(r"\s+")
NON_TEXT_RE = re.compile(r"[^a-zA-Z0-9\s$%.,!?@#:/_-]")


def clean_text(text: str) -> str:
    normalized = text.lower().strip()
    normalized = NON_TEXT_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    return normalized


def tokenize(text: str) -> list[str]:
    return clean_text(text).split()

