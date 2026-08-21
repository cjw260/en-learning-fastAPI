from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import current_user, database_session
from en_learning.api.serialization import business_success
from en_learning.api.tracker_rate import enforce_tracker_rate_limit
from en_learning.common.auth import Principal, get_optional_principal
from en_learning.common.errors import AppError
from en_learning.db.models import (
    ErrorEntry,
    PageView,
    PerformanceEntry,
    TrackEvent,
    User,
    Visitor,
    utc_now_naive,
)
from en_learning.schemas.core import (
    ErrorRequest,
    EventRequest,
    PageViewRequest,
    PerformanceRequest,
    UpdateVisitorRequest,
    VisitorRequest,
)
from en_learning.schemas.envelope import SuccessEnvelope
from en_learning.services.tracker_privacy import sanitize_payload, sanitize_text, sanitize_url

logger = logging.getLogger("en_learning.api.tracker")
router = APIRouter(
    prefix="/tracker",
    dependencies=[Depends(enforce_tracker_rate_limit)],
)


async def _ensure_visitor(session: AsyncSession, visitor_id: str) -> None:
    if await session.scalar(select(Visitor.id).where(Visitor.id == visitor_id)) is None:
        raise AppError("访客不存在", status_code=404)


async def _commit_entry(
    session: AsyncSession,
    entry: PageView | TrackEvent | PerformanceEntry | ErrorEntry,
    *,
    operation: str,
) -> None:
    try:
        await _ensure_visitor(session, entry.visitor_id)
        session.add(entry)
        await session.commit()
    except AppError:
        await session.rollback()
        raise
    except (SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning("tracker.database_unavailable", extra={"operation": operation})
        raise AppError("埋点服务暂时不可用", status_code=503) from exception


@router.post("/uv", response_model=SuccessEnvelope[str])
async def upsert_visitor(
    request: Request,
    payload: VisitorRequest,
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    if payload.user_id is not None:
        if principal is None:
            raise AppError("绑定用户需要登录", status_code=401)
        if payload.user_id != principal.user_id:
            raise AppError("无权绑定其他用户", status_code=403)
    user_id = principal.user_id if principal else None
    try:
        if (
            user_id is not None
            and await session.scalar(select(User.id).where(User.id == user_id)) is None
        ):
            raise AppError("token已失效", status_code=401)
        now = utc_now_naive()
        statement = insert(Visitor.__table__).values(  # type: ignore[arg-type]
            id=uuid.uuid4().hex,
            anonymousId=payload.anonymous_id,
            userId=user_id,
            browser=sanitize_text(payload.browser) if payload.browser else None,
            os=sanitize_text(payload.os) if payload.os else None,
            device=sanitize_text(payload.device) if payload.device else None,
            createdAt=now,
            updatedAt=now,
        )
        updates: dict[str, object] = {"updatedAt": now}
        for field, column in (("browser", "browser"), ("os", "os"), ("device", "device")):
            if field in payload.model_fields_set:
                value = getattr(payload, field)
                updates[column] = sanitize_text(value) if value else None
        if user_id is not None:
            updates["userId"] = user_id
        visitor_id = await session.scalar(
            statement.on_conflict_do_update(
                index_elements=["anonymousId"],
                set_=updates,
                where=(
                    or_(Visitor.user_id.is_(None), Visitor.user_id == user_id)
                    if user_id is not None
                    else None
                ),
            ).returning(Visitor.id)
        )
        if visitor_id is None:
            raise AppError("访客已绑定其他用户", status_code=403)
        await session.commit()
    except AppError:
        await session.rollback()
        raise
    except (SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning("tracker.database_unavailable", extra={"operation": "uv"})
        raise AppError("埋点服务暂时不可用", status_code=503) from exception
    return business_success(request, visitor_id)


@router.post("/update-uv", response_model=SuccessEnvelope[bool])
async def update_visitor(
    request: Request,
    payload: UpdateVisitorRequest,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    if payload.user_id != user.id:
        raise AppError("无权绑定其他用户", status_code=403)
    try:
        visitor = await session.scalar(
            select(Visitor).where(Visitor.id == payload.visitor_id).with_for_update()
        )
        if visitor is None:
            raise AppError("访客不存在", status_code=404)
        if visitor.user_id not in (None, user.id):
            raise AppError("访客已绑定其他用户", status_code=403)
        visitor.user_id = user.id
        await session.commit()
    except AppError:
        await session.rollback()
        raise
    except (SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning("tracker.database_unavailable", extra={"operation": "update-uv"})
        raise AppError("埋点服务暂时不可用", status_code=503) from exception
    return business_success(request, True)


@router.post("/performance", response_model=SuccessEnvelope[bool])
async def performance(
    request: Request,
    payload: PerformanceRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    await _commit_entry(
        session,
        PerformanceEntry(
            id=uuid.uuid4().hex,
            visitor_id=payload.visitor_id,
            fp=payload.fp,
            fcp=payload.fcp,
            lcp=payload.lcp,
            inp=payload.inp,
            cls=payload.cls,
        ),
        operation="performance",
    )
    return business_success(request, True)


@router.post("/pv", response_model=SuccessEnvelope[bool])
async def page_view(
    request: Request,
    payload: PageViewRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    await _commit_entry(
        session,
        PageView(
            id=uuid.uuid4().hex,
            visitor_id=payload.visitor_id,
            url=sanitize_url(payload.url) or "",
            referrer=sanitize_url(payload.referrer),
            path=sanitize_text(payload.path),
        ),
        operation="pv",
    )
    return business_success(request, True)


@router.post("/event", response_model=SuccessEnvelope[bool])
async def event(
    request: Request,
    payload: EventRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    await _commit_entry(
        session,
        TrackEvent(
            id=uuid.uuid4().hex,
            visitor_id=payload.visitor_id,
            event=sanitize_text(payload.event),
            payload=sanitize_payload(payload.payload),
            url=sanitize_url(payload.url),
        ),
        operation="event",
    )
    return business_success(request, True)


@router.post("/error", response_model=SuccessEnvelope[bool])
async def error(
    request: Request,
    payload: ErrorRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    await _commit_entry(
        session,
        ErrorEntry(
            id=uuid.uuid4().hex,
            visitor_id=payload.visitor_id,
            error=sanitize_text(payload.error),
            message=sanitize_text(payload.message) if payload.message else None,
            stack=sanitize_text(payload.stack) if payload.stack else None,
            url=sanitize_url(payload.url),
        ),
        operation="error",
    )
    return business_success(request, True)
