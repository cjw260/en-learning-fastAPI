from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy import exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import current_user, database_session
from en_learning.api.serialization import business_success, word_data
from en_learning.common.errors import AppError
from en_learning.db.models import (
    Course,
    CourseRecord,
    User,
    WordBook,
    WordBookRecord,
    utc_now_naive,
)
from en_learning.schemas.core import MasterWordsRequest, MasterWordsResult, WordResult
from en_learning.schemas.envelope import SuccessEnvelope

logger = logging.getLogger("en_learning.api.learning")
router = APIRouter(prefix="/learn")
COURSE_TAGS = frozenset({"gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky"})


@router.get("/word/{id}", response_model=SuccessEnvelope[list[WordResult]])
async def course_words(
    request: Request,
    course_id: Annotated[str, Path(alias="id", min_length=1, max_length=128)],
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    course_statement = (
        select(Course)
        .join(CourseRecord, CourseRecord.course_id == Course.id)
        .where(
            Course.id == course_id,
            CourseRecord.user_id == user.id,
            CourseRecord.is_purchased.is_(True),
        )
    )
    try:
        course = await session.scalar(course_statement)
        if course is None or course.value not in COURSE_TAGS:
            raise AppError("课程未购买", status_code=403)
        learned = exists(
            select(WordBookRecord.id).where(
                WordBookRecord.word_id == WordBook.id,
                WordBookRecord.user_id == user.id,
            )
        )
        word_statement = (
            select(WordBook)
            .where(getattr(WordBook, course.value).is_(True), ~learned)
            .order_by(
                WordBook.frq_rank.asc().nulls_last(),
                WordBook.word.asc(),
                WordBook.id.asc(),
            )
            .limit(10)
        )
        words = list((await session.scalars(word_statement)).all())
    except AppError:
        raise
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("learning.database_unavailable", extra={"operation": "list"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(request, [word_data(word) for word in words])


@router.post("/word/master", response_model=SuccessEnvelope[MasterWordsResult])
async def master_words(
    request: Request,
    payload: MasterWordsRequest,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    word_ids = list(dict.fromkeys(payload.word_ids))
    try:
        purchased_values = set(
            (
                await session.scalars(
                    select(Course.value)
                    .join(CourseRecord, CourseRecord.course_id == Course.id)
                    .where(
                        CourseRecord.user_id == user.id,
                        CourseRecord.is_purchased.is_(True),
                        Course.value.in_(COURSE_TAGS),
                    )
                )
            ).all()
        )
        if not purchased_values:
            raise AppError("课程未购买", status_code=403)
        authorized_condition = or_(
            *(getattr(WordBook, value).is_(True) for value in purchased_values)
        )
        authorized_ids = set(
            (
                await session.scalars(
                    select(WordBook.id).where(
                        WordBook.id.in_(word_ids),
                        authorized_condition,
                    )
                )
            ).all()
        )
        if authorized_ids != set(word_ids):
            raise AppError("单词不属于已购买课程", status_code=403)

        now = utc_now_naive()
        values = [
            {
                "id": uuid.uuid4().hex,
                "wordId": word_id,
                "userId": user.id,
                "isMaster": True,
                "createdAt": now,
                "updatedAt": now,
            }
            for word_id in word_ids
        ]
        statement = (
            insert(WordBookRecord.__table__)  # type: ignore[arg-type]
            .values(values)
            .on_conflict_do_update(
                index_elements=["userId", "wordId"],
                set_={"isMaster": True, "updatedAt": now},
                where=WordBookRecord.is_master.is_(False),
            )
            .returning(WordBookRecord.word_id)
        )
        changed = list((await session.scalars(statement)).all())
        word_number = await session.scalar(
            update(User)
            .where(User.id == user.id)
            .values(word_number=User.word_number + len(changed))
            .returning(User.word_number)
        )
        await session.commit()
    except AppError:
        await session.rollback()
        raise
    except (SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning("learning.database_unavailable", extra={"operation": "master"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(request, {"wordNumber": int(word_number or 0)})
