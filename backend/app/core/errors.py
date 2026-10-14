class AppError(Exception):
    """Mapped to a JSON HTTP error by the FastAPI exception handler."""

    def __init__(self, message: str, *, code: str = "app_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class InvalidOptimizationInputError(AppError):
    """The optimizer inputs do not make sense together."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_optimization_input", status_code=422)


class InfeasibleAllocationRulesError(AppError):
    """The allocation rules cannot be met. For example, the maximum weight is too small for the number of stocks."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="infeasible_allocation_rules", status_code=422)


class OptimizationFailedError(AppError):
    """The solver did not find a reliable allocation for the inputs."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="optimization_failed", status_code=422)
        
        
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


class InvalidTickerFormatError(AppError):
    """The ticker symbol does not have a valid format."""

    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"'{symbol}' is not a valid ticker symbol. Check the symbol and try again.",
            code="invalid_ticker_format",
            status_code=422,
        )


class UnsupportedSecurityError(AppError):
    """The ticker is known, but the application does not support its security type."""

    def __init__(self, symbol: str, security_type: str | None) -> None:
        super().__init__(
            f"Ticker '{symbol}' is a security type that is not supported ({security_type}).",
            code="unsupported_security",
            status_code=422,
        )


class InvalidSearchQueryError(AppError):
    """The search text is empty."""

    def __init__(self) -> None:
        super().__init__(
            "Enter a ticker or company name to search.",
            code="invalid_search_query",
            status_code=422,
        )


class InvalidDateRangeError(AppError):
    """The start date and end date cannot be used together."""

    def __init__(self, message: str = "Choose a start date that is before the end date.") -> None:
        super().__init__(message, code="invalid_date_range", status_code=422)


class UnreliablePriceHistoryError(AppError):
    """The price rows have gaps or values that are not safe to store."""

    def __init__(
        self,
        message: str = "The price history has missing or invalid values. Choose another range or symbol.",
    ) -> None:
        super().__init__(message, code="unreliable_price_history", status_code=422)


class InsufficientHistoryError(AppError):
    """There are not enough price rows for the requested range."""

    def __init__(
        self,
        message: str = "There is not enough price history for this symbol and date range.",
    ) -> None:
        super().__init__(message, code="insufficient_history", status_code=422)


class InvalidCalculationInputError(AppError):
    """The calculation request or configuration is not usable."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_calculation_input", status_code=422)


class InvalidPriceHistoryError(AppError):
    """Stored prices cannot be used for return calculations."""

    def __init__(
        self,
        message: str = "The price history has invalid values for calculation.",
    ) -> None:
        super().__init__(message, code="invalid_price_history", status_code=422)


class InvalidCalculationResultError(AppError):
    """A calculation produced a non-finite or unusable result."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_calculation_result", status_code=422)
