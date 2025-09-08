# app_package/config.py
"""
Configuration settings for the TrueTag backend.
Loads environment variables from .env using pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn
from typing import Optional


class AppSettings(BaseSettings):
    DATABASE_URL: PostgresDsn
    # Use a modern default or remove if not used
    PG_VERSION: str = "16.0"
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Cache settings for MVP (in-memory)
    CACHE_EXPIRATION_SECONDS: int = 3600
    DB_ECHO: bool = False  #

    # Blockchain settings
    BLOCKCHAIN_RPC: str
    CONTRACT_ADDRESS: str
    ADMIN_WALLET: str
    ADMIN_PRIVATE_KEY: str

    # File storage settings
    STATIC_DIR: str = "static/uploads"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = AppSettings()