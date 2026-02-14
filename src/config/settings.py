"""Silicon-Empire configuration module."""

from pydantic_settings import BaseSettings
from pydantic import Field


class ModelConfig(BaseSettings):
    """OpenRouter model assignments per agent role."""

    gm: str = Field(default="deepseek/deepseek-chat-v3-0324", alias="MODEL_GM")
    cgo: str = Field(default="deepseek/deepseek-chat-v3-0324", alias="MODEL_CGO")
    coo: str = Field(default="deepseek/deepseek-chat-v3-0324", alias="MODEL_COO")
    cro: str = Field(default="deepseek/deepseek-chat-v3-0324", alias="MODEL_CRO")
    cto: str = Field(default="anthropic/claude-sonnet-4", alias="MODEL_CTO")
    creative: str = Field(default="anthropic/claude-sonnet-4", alias="MODEL_CREATIVE")
    analysis: str = Field(default="google/gemini-2.5-flash", alias="MODEL_ANALYSIS")

    model_config = {"env_file": ".env", "extra": "ignore"}


class Settings(BaseSettings):
    """Global application settings loaded from environment."""

    # === OpenRouter ===
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_app_name: str = Field(default="silicon-empire", alias="OPENROUTER_APP_NAME")

    # === PostgreSQL (本地) ===
    database_url: str = Field(
        default="postgresql://silicon:silicon2026@localhost:5432/silicon_empire",
        alias="DATABASE_URL",
    )
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="silicon_empire", alias="POSTGRES_DB")
    postgres_user: str = Field(default="silicon", alias="POSTGRES_USER")
    postgres_password: str = Field(default="silicon2026", alias="POSTGRES_PASSWORD")

    # === Redis ===
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # === Feishu (6-Bot) ===
    feishu_decision_chat_id: str = Field(default="", alias="FEISHU_DECISION_CHAT_ID")
    feishu_execution_chat_id: str = Field(default="", alias="FEISHU_EXECUTION_CHAT_ID")
    feishu_alert_chat_id: str = Field(default="", alias="FEISHU_ALERT_CHAT_ID")

    # === Gmail ===
    gmail_credentials_path: str = Field(
        default="./secrets/gmail_credentials.json", alias="GMAIL_CREDENTIALS_PATH"
    )

    # === Shopify ===
    shopify_store_url: str = Field(default="", alias="SHOPIFY_STORE_URL")
    shopify_access_token: str = Field(default="", alias="SHOPIFY_ACCESS_TOKEN")

    # === System Config ===
    max_iteration_count: int = Field(default=5, alias="MAX_ITERATION_COUNT")
    token_budget_per_session: int = Field(default=50000, alias="TOKEN_BUDGET_PER_SESSION")
    auto_approve_profit_threshold: float = Field(
        default=20.0, alias="AUTO_APPROVE_PROFIT_THRESHOLD"
    )
    auto_approve_risk_threshold: int = Field(default=2, alias="AUTO_APPROVE_RISK_THRESHOLD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "extra": "ignore"}


# Singleton instances
_settings: Settings | None = None
_models: ModelConfig | None = None


def get_settings() -> Settings:
    """Get or create the global Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


def get_models() -> ModelConfig:
    """Get or create the ModelConfig singleton."""
    global _models
    if _models is None:
        _models = ModelConfig()  # type: ignore[call-arg]
    return _models
