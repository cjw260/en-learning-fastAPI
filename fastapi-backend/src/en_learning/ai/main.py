from fastapi import FastAPI

from en_learning.ai.router import router
from en_learning.common.application import ServiceKind, create_http_application
from en_learning.common.config import Settings


def create_app() -> FastAPI:
    app = create_http_application(ServiceKind.AI, settings=Settings())
    app.include_router(router)
    return app
