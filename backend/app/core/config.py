from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


COMMUNITY_TITLE_MAX = 160
COMMUNITY_POST_BODY_MAX = 10000
COMMUNITY_REPLY_BODY_MAX = 4000
COMMUNITY_PROFILE_NAME_MAX = 80
COMMUNITY_AVATAR_URL_MAX = 2048


class Settings(BaseSettings):
    """Runtime settings. Copy `.env.example` to `.env` and adjust locally."""

    database_url: str = "postgresql+psycopg2://optify:optify@localhost:5432/optify"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    clerk_issuer: str = ""
    clerk_jwt_key: str = ""
    community_avatar_hosts: str = "images.clerk.dev,img.clerk.com"
    community_page_size: int = 20
    community_page_max: int = 50
    # Fernet key for per-user brokerage BYOK secrets (url-safe base64, 32 bytes).
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credentials_fernet_key: str = ""
    # Public HTTPS origin of this API (no trailing slash). Used as Schwab OAuth redirect_uri host.
    public_api_base_url: str = "https://127.0.0.1:8000"
    # Where to send the browser after Schwab OAuth completes (no trailing slash).
    frontend_app_url: str = "http://127.0.0.1:5173"
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
    # The CVXPY solver for all optimization strategies (Decision 005, "Rules").
    optimization_solver: str = "CLARABEL"
    default_risk_free_rate: float = 0.04
    # An optimization needs at least the larger of these numbers of shared daily returns:
    # the minimum, or the minimum per stock x the number of stocks (Decision 005, "Minimum history").
    min_return_observations: int = 60
    min_return_observations_per_stock: int = 10
    # The U.S. equity risk premium that Kroll recommends, for the Black–Litterman prior (Decision 009).
    equity_risk_premium: float = 0.05
    # The market index for the Black–Litterman prior: the S&P 500 ETF (Decision 009).
    market_proxy_ticker: str = "SPY"
    # The uncertainty of the Black–Litterman prior, from He and Litterman, 1999 (Decision 009).
    black_litterman_tau: float = 0.05
    portfolio_chart_initial_capital: float = 100_000.0
    # Yahoo symbols use letters, digits, and ".", "-", "^", "=" (for example BRK-B, RY.TO).
    ticker_pattern: str = r"[A-Z0-9.\-^=]{1,15}"
    supported_security_types: str = "EQUITY,ETF"
    # Gemini assistant (Decision 013). Empty key disables chat routes with a clear 503.
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"
    chat_rag_top_k: int = 6
    # gemini-embedding-001 supports Matryoshka dims; we store 768.
    chat_embedding_dimensions: int = 768
    chat_pending_tool_ttl_seconds: int = 600

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

    @property
    def schwab_oauth_callback_url(self) -> str:
        return f"{self.public_api_base_url.rstrip('/')}/api/brokerage-credentials/schwab/callback"

    @property
    def settings_oauth_redirect_url(self) -> str:
        return f"{self.frontend_app_url.rstrip('/')}/settings"


@lru_cache
def get_settings() -> Settings:
    return Settings()
