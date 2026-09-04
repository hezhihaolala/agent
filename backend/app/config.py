from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/guiyuan.db"
    archive_dir: Path = Path("./data/archives")
    admin_username: str = "admin"
    admin_password: str = "change-me-before-production"
    session_cookie_secure: bool = False
    session_ttl_hours: int = 24

    model_config = SettingsConfigDict(
        env_prefix="GUIYUAN_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_password(self) -> "Settings":
        if (
            self.environment == "production"
            and self.admin_password == "change-me-before-production"
        ):
            raise ValueError("生产环境必须设置 GUIYUAN_ADMIN_PASSWORD")
        return self
