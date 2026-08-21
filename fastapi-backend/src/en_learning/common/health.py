import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from en_learning.common.responses import failure_response, success_response
from en_learning.schemas.envelope import FailureEnvelope, SuccessEnvelope
from en_learning.schemas.health import HealthPayload
from en_learning.services.resources import ManagedResources, ReadinessCheck


async def _run_check(
    check: ReadinessCheck,
    timeout_seconds: float,
) -> Literal["up", "down"]:
    try:
        async with asyncio.timeout(timeout_seconds):
            await check()
    except Exception:
        return "down"
    return "up"


def create_health_router(service_name: str) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", response_model=SuccessEnvelope[HealthPayload])
    async def live(request: Request) -> JSONResponse:
        return success_response(
            request,
            HealthPayload(status="alive", service=service_name).model_dump(exclude_none=True),
        )

    @router.get(
        "/ready",
        response_model=SuccessEnvelope[HealthPayload],
        responses={503: {"model": FailureEnvelope}},
    )
    async def ready(request: Request) -> JSONResponse:
        resources: ManagedResources = request.app.state.resources
        timeout: float = request.app.state.settings.health_check_timeout_seconds
        checks = resources.readiness_checks()
        names = list(checks)
        statuses = await asyncio.gather(*(_run_check(checks[name], timeout) for name in names))
        results = dict(zip(names, statuses, strict=True))
        if any(status == "down" for status in results.values()):
            return failure_response(
                request,
                message="Service not ready",
                status_code=503,
                details={"checks": results},
            )
        return success_response(
            request,
            HealthPayload(status="ready", service=service_name, checks=results).model_dump(),
        )

    return router
