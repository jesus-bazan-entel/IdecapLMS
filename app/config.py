"""
Configuration settings for ApoloLMS API
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # JWT Configuration
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Firebase
    firebase_project_id: str = "apololms"
    firebase_service_account_path: str = "./firebase-service-account.json"
    firebase_storage_bucket: str = "apololms.firebasestorage.app"

    # Google AI (Gemini)
    google_api_key: str = ""
    gemini_api_key: str = ""  # Alias for google_api_key

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # HeyGen API
    heygen_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://apololms.web.app,https://apololms.firebaseapp.com"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
