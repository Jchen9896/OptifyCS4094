class AppError(Exception):
    """Mapped to a JSON HTTP error by the FastAPI exception handler."""

    def __init__(self, message: str, *, code: str = "app_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class MarketDataUnavailableError(AppError):
    """The market data source failed or did not respond."""

    def __init__(self, message: str = "Market data is not available now. Try again later.") -> None:
        super().__init__(message, code="market_data_unavailable", status_code=503)


class TickerNotFoundError(AppError):
    """The market data source does not know the ticker symbol."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Ticker '{symbol}' was not found. Check the symbol and try again.",
            code="ticker_not_found",
            status_code=404,
        )
