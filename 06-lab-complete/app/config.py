"""Application configuration loaded from environment variables."""
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Storage
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Security
    agent_api_key: str = Field(default="secret-key-123", alias="AGENT_API_KEY")

    # Reliability guards
    rate_limit_per_minute: int = Field(default=10, alias="RATE_LIMIT_PER_MINUTE")
    monthly_budget_usd: float = Field(default=10.0, alias="MONTHLY_BUDGET_USD")

    # Chat behavior
    max_history_turns: int = Field(default=20, alias="MAX_HISTORY_TURNS")
    conversation_ttl_seconds: int = Field(default=604800, alias="CONVERSATION_TTL_SECONDS")
    llm_model: str = Field(default="mock-llm-v1", alias="LLM_MODEL")

    # CORS
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"], alias="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


settings = Settings()
