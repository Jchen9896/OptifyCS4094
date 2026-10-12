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
