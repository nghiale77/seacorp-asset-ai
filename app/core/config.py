"""Cấu hình trung tâm, nạp từ biến môi trường / file .env. Không hard-code secrets."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Neo theo thư mục gốc project, KHÔNG dựa vào CWD của tiến trình gọi (Streamlit/
# uvicorn có thể được khởi động từ một working directory khác), để .env và
# đường dẫn SQLite mặc định luôn được tìm/tạo đúng chỗ dù chạy từ đâu.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "seacorp_asset_dev.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore",
    )

    database_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    db_schema: str = "seacorp_asset"

    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5"

    secret_key: str = "change-me-dev-only-not-for-production"
    access_token_expire_minutes: int = 480

    intake_provider: str = "manual_intake"

    ms_graph_client_id: str = ""
    ms_graph_client_secret: str = ""
    ms_graph_tenant_id: str = ""
    gmail_credentials_json: str = ""
    teams_webhook_url: str = ""

    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
