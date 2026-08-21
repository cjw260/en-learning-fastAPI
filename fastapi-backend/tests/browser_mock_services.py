"""Local-only upstreams for reproducible P03 browser acceptance.

Run on port 3000 for the legacy Core API surface and on another local port for
the DeepSeek-compatible endpoint. It never contacts external services.
"""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

USER_ID = "p03-browser-user"
JWT_SECRET = "p03-browser-secret"


def _segment(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def access_token() -> str:
    header = _segment({"alg": "HS256", "typ": "JWT"})
    payload = _segment(
        {
            "userId": USER_ID,
            "name": "P03 浏览器验收",
            "tokenType": "access",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3_600,
        }
    )
    signed = f"{header}.{payload}"
    signature = hmac.new(JWT_SECRET.encode(), signed.encode(), hashlib.sha256).digest()
    return f"{signed}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def envelope(data: Any) -> JSONResponse:
    return JSONResponse(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "path": "/api/v1/browser-acceptance",
            "message": "请求成功",
            "code": 200,
            "success": True,
            "data": data,
        }
    )


app = FastAPI(title="P03 browser acceptance mocks")


@app.post("/api/v1/user/login")
async def login() -> JSONResponse:
    return envelope(
        {
            "id": USER_ID,
            "name": "P03 浏览器验收",
            "email": "p03-browser@example.test",
            "phone": "13800000000",
            "address": None,
            "avatar": None,
            "bio": None,
            "isTimingTask": False,
            "timingTaskTime": "00:00:00",
            "wordNumber": 0,
            "dayNumber": 0,
            "createdAt": datetime.now(UTC).isoformat(),
            "updatedAt": datetime.now(UTC).isoformat(),
            "lastLoginAt": None,
            "token": {"accessToken": access_token(), "refreshToken": "browser-refresh"},
        }
    )


@app.post("/api/v1/tracker/uv")
async def tracker_uv() -> JSONResponse:
    return envelope("p03-browser-visitor")


@app.post("/api/v1/tracker/{operation}")
async def tracker_operation(operation: str) -> JSONResponse:
    del operation
    return envelope(None)


@app.post("/chat/completions")
async def chat_completions(payload: dict[str, Any]) -> StreamingResponse:
    deep_think = payload.get("model") == "deepseek-reasoner"

    async def events() -> AsyncGenerator[str]:
        if deep_think:
            yield 'data: {"choices":[{"delta":{"reasoning_content":"深度分析"}}]}\n\n'
            yield 'data: {"choices":[{"delta":{"content":"深度模式回答"}}]}\n\n'
        else:
            yield 'data: {"choices":[{"delta":{"content":"普通模式回答"}}]}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
