from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Customer Complaint Classification & Routing Engine"
    app_env: str = "local"
    database_url: str = "sqlite:///./complaints.db"
    cors_origins: list[str] | str = ["http://localhost:8501", "http://127.0.0.1:8501"]

    llm_provider: Literal["disabled", "ollama", "openai_compatible"] = Field(
        default="disabled",
        validation_alias=AliasChoices("LLM_PROVIDER", "QWEN_PROVIDER"),
    )
    llm_api_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("LLM_API_BASE_URL", "QWEN_API_BASE_URL"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "QWEN_API_KEY"),
    )
    llm_model: str = Field(
        default="llama3.2",
        validation_alias=AliasChoices("LLM_MODEL", "QWEN_MODEL"),
    )
    llm_timeout_seconds: float = Field(
        default=20,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "QWEN_TIMEOUT_SECONDS"),
    )
    use_llm_classifier: bool = Field(
        default=True,
        validation_alias=AliasChoices("USE_LLM_CLASSIFIER", "USE_QWEN_CLASSIFIER"),
    )

    model_path: str = "models/complaint_classifier.joblib"
    sla_poll_seconds: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: list[str] | str) -> list[str]:
        if isinstance(value, str):
            if value.strip() == "*":
                return ["*"]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("llm_timeout_seconds", mode="before")
    @classmethod
    def parse_llm_timeout_seconds(cls, value: float | str | None) -> float:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 20
        return float(value)

    @field_validator("sla_poll_seconds", mode="before")
    @classmethod
    def parse_sla_poll_seconds(cls, value: int | str | None) -> int:
        if value is None or (isinstance(value, str) and not value.strip()):
            return 15
        return int(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
