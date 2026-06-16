from functools import lru_cache
from typing import Literal


class Settings:
    _defaults = {
        "app_name": "Customer Complaint Classification & Routing Engine",
        "app_env": "local",
        "database_url": "sqlite:///./complaints.db",
        "cors_origins": ["http://localhost:8501", "http://127.0.0.1:8501"],
        "llm_provider": "openai_compatible",
        "llm_api_base_url": "http://localhost:8000/v1",
        "llm_api_key": "abc-123",
        "llm_model": "Qwen3-30B-A3B",
        "llm_timeout_seconds": 90.0,
        "use_llm_classifier": True,
        "model_path": "models/complaint_classifier.joblib",
        "sla_poll_seconds": 15,
    }

    app_name: str
    app_env: str
    database_url: str
    cors_origins: list[str]

    llm_provider: Literal["disabled", "ollama", "openai_compatible"]
    llm_api_base_url: str
    llm_api_key: str | None
    llm_model: str
    llm_timeout_seconds: float
    use_llm_classifier: bool

    model_path: str
    sla_poll_seconds: int

    def __init__(self, **overrides):
        values = dict(self._defaults)

        for key, value in overrides.items():
            values[key.lower()] = value

        values["cors_origins"] = _as_list(values["cors_origins"])
        values["llm_api_key"] = values["llm_api_key"] or None
        values["llm_timeout_seconds"] = float(values["llm_timeout_seconds"])
        values["use_llm_classifier"] = _as_bool(values["use_llm_classifier"])
        values["sla_poll_seconds"] = int(values["sla_poll_seconds"])
        values["llm_api_base_url"] = _normalize_base_url(
            str(values["llm_api_base_url"]),
            str(values["llm_provider"]),
        )

        for key, value in values.items():
            setattr(self, key, value)


def _as_bool(value: bool | str) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: list[str] | str) -> list[str]:
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_base_url(base_url: str, provider: str) -> str:
    normalized = base_url.rstrip("/")
    if provider == "openai_compatible" and not normalized.endswith("/v1"):
        return f"{normalized}/v1"
    return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
