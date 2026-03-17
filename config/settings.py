from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from config.env import get_env, get_env_path, load_dotenv


class Settings(BaseModel):
    app_name: str = "AlphaAgent"
    env: str = Field(default_factory=lambda: get_env("APP_ENV", "dev") or "dev")

    gemini_api_key: str | None = Field(default_factory=lambda: get_env("GEMINI_API_KEY"))
    gemini_base_url: str | None = Field(
        default_factory=lambda: get_env(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    )
    gemini_model: str = Field(
        default_factory=lambda: get_env("GEMINI_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash"
    )
    fmp_api_key: str | None = Field(default_factory=lambda: get_env("FMP_API_KEY"))
    news_api_key: str | None = Field(default_factory=lambda: get_env("NEWS_API_KEY"))
    filings_api_key: str | None = Field(default_factory=lambda: get_env("FILINGS_API_KEY"))
    transcript_api_key: str | None = Field(default_factory=lambda: get_env("TRANSCRIPT_API_KEY"))
    market_data_api_key: str | None = Field(default_factory=lambda: get_env("MARKET_DATA_API_KEY"))

    vector_db: str = Field(default_factory=lambda: get_env("VECTOR_DB", "chroma") or "chroma")
    cache_dir: Path = Field(default_factory=lambda: get_env_path("CACHE_DIR", "./storage/cache"))
    vector_db_path: Path = Field(default_factory=lambda: get_env_path("VECTOR_DB_PATH", "./storage/vector_db"))
    export_dir: Path = Field(default_factory=lambda: get_env_path("EXPORT_DIR", "./storage/exports"))
    ideas_dir: Path = Field(default_factory=lambda: get_env_path("IDEAS_DIR", "./storage/ideas"))

    opportunity_universe: list[str] = Field(
        default_factory=lambda: ["NVDA", "AMD", "TSM"]
    )

    def ensure_storage_dirs(self) -> None:
        for path in (self.cache_dir, self.vector_db_path, self.export_dir, self.ideas_dir):
            path.mkdir(parents=True, exist_ok=True)

    def validate_startup(self) -> None:
        self.ensure_storage_dirs()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    settings = Settings()
    settings.validate_startup()
    return settings
