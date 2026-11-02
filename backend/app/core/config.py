from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Đọc cấu hình từ biến môi trường / file .env (tên biến không phân biệt hoa thường)."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Hệ thống Quản lý & Đăng ký Học phần"
    environment: str = "dev"  # dev | test | prod

    database_url: str = ""
    mysql_database: str = "qldt"
    mysql_user: str = "app"
    mysql_password: str = Field(default="", min_length=0)
    mysql_host: str = "localhost"
    mysql_port: int = 3306

    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 3600  # theo quy ước API: token sống 3600 giây, không refresh

    min_credits_per_semester: int = 12
    max_credits_per_semester: int = Field(default=24, ge=1)

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    timezone: str = "Asia/Ho_Chi_Minh"  # +07:00
    receipt_logo_path: str | None = None
    receipt_font_path: str | None = None

    @model_validator(mode="after")
    def validate_credit_limits_and_database_url(self) -> "Settings":
        if self.max_credits_per_semester < self.min_credits_per_semester:
            raise ValueError(
                "MAX_CREDITS_PER_SEMESTER phải lớn hơn hoặc bằng MIN_CREDITS_PER_SEMESTER"
            )
        if not self.database_url:
            self.database_url = URL.create(
                "mysql+pymysql",
                username=self.mysql_user,
                password=self.mysql_password,
                host=self.mysql_host,
                port=self.mysql_port,
                database=self.mysql_database,
                query={"charset": "utf8mb4"},
            ).render_as_string(hide_password=False)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
