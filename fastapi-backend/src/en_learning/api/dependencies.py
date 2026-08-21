from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.common.auth import Principal, get_current_principal
from en_learning.common.errors import AppError
from en_learning.db.models import User
from en_learning.services.resources import CoreResources


def core_resources(request: Request) -> CoreResources:
    return cast(CoreResources, request.app.state.resources)


async def database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with core_resources(request).database.session() as session:
        yield session


async def current_user(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> User:
    try:
        user = await session.scalar(select(User).where(User.id == principal.user_id))
    except (SQLAlchemyError, OSError) as exception:
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    if user is None:
        raise AppError("token已失效", status_code=401)
    return user
