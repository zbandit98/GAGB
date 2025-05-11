"""Configuration settings for the GAGB application."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    draftkings_api_key: Optional[str] = Field(None, env="DRAFTKINGS_API_KEY")
    fanduel_api_key: Optional[str] = Field(None, env="FANDUEL_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    espn_api_key: Optional[str] = Field(None, env="ESPN_API_KEY")
    the_athletic_api_key: Optional[str] = Field(None, env="THE_ATHLETIC_API_KEY")

    # Database
    database_url: str = Field("sqlite:///./gagb.db", env="DATABASE_URL")

    # FastAPI
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    debug: bool = Field(False, env="DEBUG")

    # Security (for future authentication)
    secret_key: str = Field("default_secret_key", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # Application settings
    app_name: str = "GAGB - Generative AI Gambling Bot"
    app_description: str = "A sports betting decision assistant that leverages news sources, sportsbook APIs, and generative AI."
    app_version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
