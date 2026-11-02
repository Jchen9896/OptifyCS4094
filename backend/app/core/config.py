from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Copy `.env.example` to `.env` and adjust locally."""

    database_url: str = "postgresql+psycopg2://optify:optify@localhost:5432/optify"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    market_data_interval: str = "1d"
    market_data_auto_adjust: bool = True
    market_data_search_limit: int = 10
    # Provenance and limits for stored price history (Decision 006).
    market_data_source: str = "yfinance"
    market_data_calendar: str = "XNYS"
    market_data_max_span_days: int = 3650
    # Calculation and optimization defaults (Decision 005 portfolio optimizer).
    annualization_factor: float = 252.0
    optimization_tolerance: float = 1e-5
    default_risk_free_rate: float = 0.04
    # An optimization needs at least the larger of these numbers of shared daily returns:
    # the minimum, or the minimum per stock x the number of stocks (Decision 005, "Minimum history").
    min_return_observations: int = 60
    min_return_observations_per_stock: int = 10
    portfolio_chart_initial_capital: float = 100_000.0
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

    @property
    def market_data_adjustment_basis(self) -> str:
        """How stored closes were adjusted when they were fetched."""
        if self.market_data_auto_adjust:
            return "split_dividend_adjusted"
        return "raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()
