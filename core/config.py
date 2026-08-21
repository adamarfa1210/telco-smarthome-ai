"""Application Settings and Configuration Management."""
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server Info
    PROJECT_NAME: str = "TelcoCare Cloud AI Orchestrator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Gateway
    SECRET_KEY: str = "secret-super-key-change-in-prod-telcocare-cloud-2026"
    API_KEY_HEADER_NAME: str = "X-API-Key"
    ROUTER_API_SECRET: str = "openwrt-edge-router-secret-2026"
    ALLOWED_ORIGINS: List[str] = ["*"]
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120

    # LLM Settings (OpenAI-compatible or Local Qwen / vLLM Endpoint)
    LLM_API_KEY: str = "dummy-or-env-provided-key"
    LLM_MODEL: str = "qwen2.5-72b-instruct"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1024

    # Integrations
    BILLING_API_BASE_URL: str = "https://billing-internal.telco.operator.net/v1"
    BILLING_API_KEY: str = "billing-telco-core-key-default"
    TUYA_API_BASE_URL: str = "https://openapi.tuyaus.com/v1.0"
    TUYA_CLIENT_ID: str = "tuya_default_client_id"
    TUYA_CLIENT_SECRET: str = "tuya_default_client_secret"
    EDGE_CPE_DEFAULT_TIMEOUT_SEC: float = 5.0

    # Redis & DB (Optional / State Persistence)
    REDIS_URL: str = "redis://localhost:6379/0"
    DATABASE_URL: str = "postgresql+asyncpg://telco:telcopass@localhost:5432/cloud_ai_db"


settings = Settings()
