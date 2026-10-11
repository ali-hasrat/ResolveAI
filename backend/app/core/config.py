from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ResolveAI project root:
# E:\Coding\ResolveAI
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "ResolveAI"
    app_env: str = "development"

    database_url: str

    groq_api_key: str = ""

    jwt_secret_key: str

    cors_origins: str = "http://localhost:5173"

    chroma_persist_directory: str = "./data/chroma"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()