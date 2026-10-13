from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Copy `.env.example` to `.env` and adjust locally."""

    database_url: str = "postgresql+psycopg2://optify:optify@localhost:5432/optify"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    market_data_interval: str = "1d"
    market_data_auto_adjust: bool = True
    market_data_search_limit: int = 10
    # Yahoo symbols use letters, digits, and ".", "-", "^", "=" (for example BRK-B, RY.TO).
    ticker_pattern: str = r"[A-Z0-9.\-^=]{1,15}"
    supported_security_types: str = "EQUITY,ETF"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def supported_security_type_list(self) -> list[str]:
        return [kind.strip().upper() for kind in self.supported_security_types.split(",") if kind.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
