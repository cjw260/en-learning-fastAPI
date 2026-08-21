import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import current_user, database_session
from en_learning.api.serialization import business_success, course_data
from en_learning.common.errors import AppError
from en_learning.db.models import Course, CourseRecord, PaymentRecord, TradeStatus, User
from en_learning.schemas.core import CourseResult
from en_learning.schemas.envelope import SuccessEnvelope

logger = logging.getLogger("en_learning.api.courses")
router = APIRouter(prefix="/course")


@router.get("/list", response_model=SuccessEnvelope[list[CourseResult]])
async def course_list(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    try:
        courses = list((await session.scalars(select(Course).order_by(Course.created_at))).all())
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("course.database_unavailable", extra={"operation": "list"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(request, [course_data(course) for course in courses])


@router.get("/my", response_model=SuccessEnvelope[list[CourseResult]])
async def my_courses(
    request: Request,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    statement = (
        select(Course)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .join(PaymentRecord, PaymentRecord.id == CourseRecord.payment_record_id)
        .where(
            CourseRecord.user_id == user.id,
            PaymentRecord.trade_status.in_([TradeStatus.TRADE_SUCCESS, TradeStatus.TRADE_FINISHED]),
        )
        .order_by(CourseRecord.created_at)
    )
    try:
        courses = list((await session.scalars(statement)).all())
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("course.database_unavailable", extra={"operation": "my"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(request, [course_data(course) for course in courses])
