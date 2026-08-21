from __future__ import annotations

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from en_learning.common.responses import failure_response


class RequestBodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        tracker_max_bytes: int,
        avatar_max_bytes: int,
    ) -> None:
        self._app = app
        self._tracker_max_bytes = tracker_max_bytes
        self._avatar_max_bytes = avatar_max_bytes

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        message: str,
    ) -> None:
        response = failure_response(
            Request(scope),
            message=message,
            status_code=413,
        )
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.startswith("/api/v1/tracker/"):
            max_bytes = self._tracker_max_bytes
            error_message = "埋点载荷过大"
        elif path == "/api/v1/user/upload-avatar":
            max_bytes = self._avatar_max_bytes + 64 * 1024
            error_message = "文件大小不能超过5MB"
        else:
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    await self._reject(
                        scope,
                        receive,
                        send,
                        message=error_message,
                    )
                    return
            except ValueError:
                pass

        buffered: list[Message] = []
        total = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] == "http.disconnect":
                break
            total += len(message.get("body", b""))
            if total > max_bytes:
                await self._reject(
                    scope,
                    receive,
                    send,
                    message=error_message,
                )
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if buffered:
                return buffered.pop(0)
            return {"type": "http.disconnect"}

        await self._app(scope, replay, send)
