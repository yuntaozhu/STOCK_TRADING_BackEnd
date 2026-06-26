import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "A-Share Financial Data API"
    APP_VERSION: str = "3.2.3"
    DEBUG: bool = False
    
    # API Keys
    IWENCAI_API_KEY: str = Field(default="", env="IWENCAI_API_KEY")
    IWENCAI_BASE_URL: str = Field(default="https://openapi.iwencai.com", env="IWENCAI_BASE_URL")
    
    # Eastmoney Limiter Settings
    EM_MIN_INTERVAL: float = 1.0  # seconds between calls to avoid ban
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
