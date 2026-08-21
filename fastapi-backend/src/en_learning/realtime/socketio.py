from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs

import socketio

from en_learning.common.auth import decode_access_token
from en_learning.common.config import Settings

logger = logging.getLogger("en_learning.realtime")


def _auth_token(auth: Any) -> str | None:
    if not isinstance(auth, dict):
        return None
    value = auth.get("token") or auth.get("Authorization")
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value or None


def create_socket_server(settings: Settings) -> socketio.AsyncServer:
    manager = socketio.AsyncRedisManager(
        str(settings.redis_url),
        channel=settings.socket_redis_channel,
    )
    server = socketio.AsyncServer(
        async_mode="asgi",
        client_manager=manager,
        cors_allowed_origins=settings.socket_allowed_origins_list,
        logger=False,
        engineio_logger=False,
    )

    @server.event  # type: ignore[untyped-decorator]
    async def connect(sid: str, environ: dict[str, Any], auth: Any) -> bool:
        token = _auth_token(auth)
        if token is None:
            logger.warning("socket.connection_rejected", extra={"reason": "missing_token"})
            return False
        try:
            principal = decode_access_token(token, settings)
        except ValueError:
            logger.warning("socket.connection_rejected", extra={"reason": "invalid_token"})
            return False
        query = parse_qs(str(environ.get("QUERY_STRING", "")), keep_blank_values=True)
        legacy_user_ids = query.get("userId", [])
        if legacy_user_ids and legacy_user_ids != [principal.user_id]:
            logger.warning("socket.connection_rejected", extra={"reason": "identity_mismatch"})
            return False
        await server.save_session(sid, {"userId": principal.user_id})
        await server.enter_room(sid, f"user_{principal.user_id}")
        logger.info("socket.connection_accepted")
        return True

    return server


class SocketPublisher:
    def __init__(self, settings: Settings) -> None:
        self.manager = socketio.AsyncRedisManager(
            str(settings.redis_url),
            channel=settings.socket_redis_channel,
            write_only=True,
        )

    async def payment_success(self, user_id: str) -> None:
        await self.manager.emit(
            "paymentSuccess",
            user_id,
            namespace="/",
            room=f"user_{user_id}",
        )

    async def close(self) -> None:
        redis_client = getattr(self.manager, "redis", None)
        if redis_client is not None:
            await redis_client.aclose()
