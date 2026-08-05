"""
Central configuration.

All secrets and environment-specific values are read from environment
variables (see .env.example). Model names and prices change often, so they are
kept here in config (never hardcoded deep in the code) and can be overridden via
env without touching source.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # --- Database (Railway Postgres) ---
    database_url: str = Field(default="")

    # --- AI providers ---
    anthropic_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # Model identifiers are config, not constants. Override in env if a newer
    # model ships. See docs/PROJECT_MEMORY.md for the model-agnostic layer plan.
    claude_text_model: str = Field(default="claude-sonnet-5")
    gemini_image_model: str = Field(default="gemini-3-pro-image")  # "Nano Banana Pro"
    openai_image_model: str = Field(default="gpt-image-1")  # fallback

    # --- Storage (Google Drive API) ---
    # Path to the service-account JSON, or the JSON contents themselves.
    google_drive_credentials_json: str = Field(default="")
    google_drive_review_folder_id: str = Field(default="")

    # --- Admin panel (basic auth) ---
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="")

    # --- Scheduling ---
    trend_sources_config: str = Field(default="config/trend_sources.yaml")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
