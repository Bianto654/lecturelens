from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database: Supabase PostgreSQL (falls back to local SQLite when empty)
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Google Gemini Flash API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Faster-Whisper + Silero VAD
    whisper_model_size: str = "large-v3-turbo"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"
    whisper_enabled: bool = True

    # Server & URLs
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_url: str = "http://127.0.0.1:8000"
    public_backend_ws_url: str = "ws://127.0.0.1:8000"
    public_app_url: str = "http://localhost:8501"

    @property
    def effective_database_url(self) -> str:
        raw = self.database_url.strip()
        if not raw:
            data_dir = Path("data")
            data_dir.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{(data_dir / 'lecturelens.db').as_posix()}"
        # Normalize Supabase postgres:// or postgresql:// URLs to psycopg3 driver
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql+psycopg://", 1)
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw

    @property
    def is_postgres(self) -> bool:
        return self.effective_database_url.startswith("postgresql")

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
