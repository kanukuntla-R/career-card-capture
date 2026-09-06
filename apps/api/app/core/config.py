from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./work/career_cards.db"
    ocr_provider: str = "mock"
    hunyuan_ocr_base_url: str = "http://127.0.0.1:8081/v1"
    hunyuan_model_name: str = "HYVL"
    hunyuan_request_timeout_seconds: float = 120.0
    google_sheets_enabled: bool = False
    google_sheet_id: str | None = None
    google_sheet_tab_name: str = "Responses"
    google_application_credentials: str | None = None
    card_image_retention: str = "delete_after_approval"
    card_image_dir: Path = Path("./work/card-images")
    web_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
