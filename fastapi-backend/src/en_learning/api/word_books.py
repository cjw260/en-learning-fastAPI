import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import database_session
from en_learning.api.serialization import business_success, word_data
from en_learning.common.errors import AppError
from en_learning.db.models import WordBook
from en_learning.schemas.core import WordListResult, WordQuery
from en_learning.schemas.envelope import SuccessEnvelope

logger = logging.getLogger("en_learning.api.word_books")
router = APIRouter(prefix="/word-book")
TAGS = ("gk", "zk", "gre", "toefl", "ielts", "cet6", "cet4", "ky")


@router.get("", response_model=SuccessEnvelope[WordListResult])
async def word_book_list(
    request: Request,
    query: Annotated[WordQuery, Query()],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    filters = []
    if query.word:
        filters.append(WordBook.word.contains(query.word))
    for tag in TAGS:
        if getattr(query, tag) is True:
            filters.append(getattr(WordBook, tag).is_(True))

    count_statement = select(func.count()).select_from(WordBook).where(*filters)
    list_statement = (
        select(WordBook)
        .where(*filters)
        .order_by(
            WordBook.frq_rank.asc().nulls_last(),
            WordBook.word.asc(),
            WordBook.id.asc(),
        )
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    try:
        total = int(await session.scalar(count_statement) or 0)
        words = list((await session.scalars(list_statement)).all())
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("word_book.database_unavailable")
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(
        request,
        {"total": total, "list": [word_data(word) for word in words]},
    )
