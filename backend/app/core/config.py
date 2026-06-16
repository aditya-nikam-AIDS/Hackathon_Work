from functools import lru_cache
from typing import Literal


class Settings:
    app_name: str = "Customer Complaint Classification & Routing Engine"
    app_env: str = "local"
    database_url: str = "sqlite:///./complaints.db"
    cors_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]

           
    llm_provider: Literal["disabled", "ollama", "openai_compatible"] = "ollama"
    llm_api_base_url: str = "http://10.42.38.125:11434"
    llm_api_key: str | None = None
    llm_model: str = "llama3.2"
    llm_timeout_seconds: float = 90
    use_llm_classifier: bool = True


    model_path: str = "models/complaint_classifier.joblib"
    sla_poll_seconds: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
