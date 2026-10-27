from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Optify API",
        description="Portfolio optimization for retail investors.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    # The default handler copies the bad input into the response. A NaN input cannot be
    # written as JSON, so the response failed with 500. This handler sends only the first
    # problem, in the same format as AppError, so the frontend can show the message.
    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        problem = exc.errors()[0]
        field = ".".join(part for part in problem["loc"][1:] if isinstance(part, str))
        message = f"{field}: {problem['msg']}." if field else f"{problem['msg']}."
        return await handle_app_error(request, AppError(message, code="invalid_request", status_code=422))

    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
