from functools import lru_cache
from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Edgarian"
    app_env: str = "development"
    dev_mode: bool = True
    log_level: str = "INFO"
    secret_key: str = "dev-insecure-key"
    tz: str = "UTC"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    sec_user_agent: str = Field(default="your@email.com", min_length=3)
    request_timeout_seconds: int = 30

    postgres_db: str = "edgarian"
    postgres_user: str = "edgarian"
    postgres_password: str = "edgarian"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = "postgresql+psycopg://edgarian:edgarian@localhost:5432/edgarian"

    pgadmin_default_email: str = "admin@edgarian.local"
    pgadmin_default_password: str = "admin"
    pgadmin_port: int = 5050

    google_client_id: str = ""
    google_client_secret: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
