import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from enum import StrEnum

from fastapi import FastAPI

from en_learning.common.config import Settings
from en_learning.common.errors import register_exception_handlers
from en_learning.common.health import create_health_router
from en_learning.common.logging import configure_logging
from en_learning.common.middleware import RequestContextMiddleware
from en_learning.services.resources import ManagedResources, ResourceSet

logger = logging.getLogger("en_learning.lifecycle")
ResourceFactory = Callable[[Settings], ManagedResources]


class ServiceKind(StrEnum):
    CORE = "core-api"
    AI = "ai-api"


def create_http_application(
    service: ServiceKind,
    *,
    settings: Settings,
    resource_factory: ResourceFactory = ResourceSet,
) -> FastAPI:
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resources = resource_factory(settings)
        app.state.settings = settings
        app.state.resources = resources
        logger.info("service.started", extra={"service": service.value})
        try:
            yield
        finally:
            await resources.close()
            logger.info("service.stopped", extra={"service": service.value})

    app = FastAPI(
        title=f"en-learning {service.value}",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Process liveness and dependency readiness."},
            {
                "name": service.value,
                "description": (
                    "P03 AI routes." if service is ServiceKind.AI else "Core API route boundary."
                ),
            },
        ],
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(create_health_router(service.value))
    return app
