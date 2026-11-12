from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_KEY = "dev-only-change-me-dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # development | test | production
    database_url: str = "postgresql+psycopg://foodbridge:foodbridge@localhost:5432/foodbridge"
    secret_key: str = _INSECURE_DEFAULT_KEY
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    auth_rate_limit_per_minute: int = 10
    pickup_rate_limit_per_minute: int = 20
    # Anti-abus
    # À passer à true en production une fois la vérification admin en place
    require_verified_claimants: bool = False
    max_active_claims: int = 3
    max_no_shows: int = 3
    max_listing_horizon_days: int = 7
    # Région utilisée pour les numéros saisis sans indicatif (06 12 ...). Code ISO à 2 lettres.
    default_phone_region: str = "FR"

    @model_validator(mode="after")
    def _forbid_default_key_in_production(self) -> "Settings":
        if self.environment == "production" and self.secret_key == _INSECURE_DEFAULT_KEY:
            raise ValueError("SECRET_KEY must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
