from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI

from en_learning.api.router import router
from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.config import Settings
from en_learning.realtime.socketio import create_socket_server


def create_app() -> FastAPI:
    settings = Settings()
    app = create_http_application(ServiceKind.CORE, settings=settings)
    app.include_router(router)
    server = create_socket_server(settings)
    socket_app = socketio.ASGIApp(server, socketio_path="socket.io")
    base_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with base_lifespan(application):
            yield
        await server.shutdown()

    app.router.lifespan_context = lifespan
    app.state.socketio = server
    app.mount("/", socket_app, name="socket.io")
    return app
