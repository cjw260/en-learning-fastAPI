import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from en_learning.common.responses import failure_response

logger = logging.getLogger("en_learning.errors")


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


async def handle_app_error(request: Request, exception: AppError) -> JSONResponse:
    return failure_response(
        request,
        message=exception.message,
        status_code=exception.status_code,
        code=exception.code,
        details=exception.details,
    )


async def handle_validation_error(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "location": [str(item) for item in error["loc"]],
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exception.errors()
    ]
    return failure_response(
        request,
        message="Validation failed",
        status_code=422,
        details={"errors": errors},
    )


async def handle_http_error(
    request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    default_message = HTTPStatus(exception.status_code).phrase
    message = exception.detail if isinstance(exception.detail, str) else default_message
    return failure_response(request, message=message, status_code=exception.status_code)


async def handle_unexpected_error(request: Request, exception: Exception) -> JSONResponse:
    logger.error(
        "request.unhandled_error",
        extra={"exceptionType": type(exception).__name__},
    )
    return failure_response(request, message="Internal server error", status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected_error)
