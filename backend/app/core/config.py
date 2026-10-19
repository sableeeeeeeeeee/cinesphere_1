"""Application settings, read from environment variables / .env file."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CineSphere"
    env: str = "dev"  # dev exposes the password-reset token in the API response (no SMTP needed)
    database_url: str = "sqlite:///./cinesphere.db"  # use postgresql+psycopg2://... in real use
    secret_key: str = "CHANGE-ME-dev-only-secret-key-change-me-please"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False  # set True behind HTTPS
    seed_demo_on_start: bool = False  # deployment helper: seeds demo data once, only if the database is empty

    seat_lock_seconds: int = 300  # 5 minutes
    max_seats_per_booking: int = 10
    tax_rate: float = 0.18  # applied to tickets-after-discount + food
    convenience_fee_per_ticket: int = 2000  # paise (Rs 20.00)

    # Development-only accounts created by the seed script
    admin_email: str = "admin@cinesphere.example.com"
    admin_password: str = "Admin@12345"
    demo_user_email: str = "demo@cinesphere.example.com"
    demo_user_password: str = "Demo@12345"

    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        # Hosting providers hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver name.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix):]
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
