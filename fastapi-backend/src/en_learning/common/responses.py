from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from en_learning.schemas.envelope import FailureEnvelope, SuccessEnvelope


def request_path(request: Request) -> str:
    path = request.url.path
    return f"{path}?{request.url.query}" if request.url.query else path


def success_response(
    request: Request,
    data: Any,
    *,
    message: str = "请求成功",
    code: int = 200,
    status_code: int = 200,
) -> JSONResponse:
    envelope = SuccessEnvelope[Any](
        timestamp=datetime.now(UTC),
        path=request_path(request),
        message=message,
        code=code,
        data=data,
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))


def failure_response(
    request: Request,
    *,
    message: str,
    status_code: int,
    code: int | None = None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    envelope = FailureEnvelope(
        timestamp=datetime.now(UTC),
        path=request_path(request),
        message=message,
        code=code if code is not None else status_code,
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(envelope, exclude_none=True),
    )
