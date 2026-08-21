from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.common.errors import AppError
from en_learning.db.models import AIChatMessage, AIChatThread, User, utc_now_naive
from en_learning.db.session import Database
from en_learning.schemas.chat import ChatRole

logger = logging.getLogger("en_learning.ai.history")
THREAD_NAMESPACE = uuid.UUID("59b2687f-773c-4ad9-9aed-a4f176787b0a")


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    role: str
    content: str
    reasoning: str | None = None


def stable_thread_id(user_id: str, role: ChatRole) -> str:
    return uuid.uuid5(THREAD_NAMESPACE, f"{user_id}\0{role.value}").hex


class ChatHistoryRepository:
    def __init__(self, database: Database, message_limit: int) -> None:
        self._database = database
        self._message_limit = message_limit

    async def _ensure_user(self, session: AsyncSession, user_id: str) -> None:
        result = await session.execute(select(User.id).where(User.id == user_id))
        if result.scalar_one_or_none() is None:
            raise AppError("token已失效", status_code=401)

    async def _ensure_thread(
        self,
        session: AsyncSession,
        user_id: str,
        role: ChatRole,
    ) -> str:
        thread_id = stable_thread_id(user_id, role)
        now = utc_now_naive()
        statement = (
            insert(AIChatThread.__table__)  # type: ignore[arg-type]
            .values(
                id=thread_id,
                userId=user_id,
                role=role.value,
                createdAt=now,
                updatedAt=now,
            )
            .on_conflict_do_nothing(index_elements=["userId", "role"])
        )
        await session.execute(statement)
        return thread_id

    async def _next_position(self, session: AsyncSession, thread_id: str) -> int:
        result = await session.execute(
            select(func.coalesce(func.max(AIChatMessage.position), 0)).where(
                AIChatMessage.thread_id == thread_id
            )
        )
        return int(result.scalar_one()) + 1

    async def append_human_and_context(
        self,
        user_id: str,
        role: ChatRole,
        content: str,
    ) -> list[ConversationMessage]:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    await self._ensure_user(session, user_id)
                    thread_id = await self._ensure_thread(session, user_id, role)
                    position = await self._next_position(session, thread_id)
                    session.add(
                        AIChatMessage(
                            id=uuid.uuid4().hex,
                            thread_id=thread_id,
                            position=position,
                            role="human",
                            content=content,
                            reasoning=None,
                        )
                    )
                    await session.flush()
                    rows = (
                        await session.execute(
                            select(AIChatMessage)
                            .where(AIChatMessage.thread_id == thread_id)
                            .order_by(AIChatMessage.position.desc())
                            .limit(self._message_limit)
                        )
                    ).scalars()
                    context = list(reversed(list(rows)))
                return [
                    ConversationMessage(
                        role=item.role,
                        content=item.content,
                        reasoning=item.reasoning,
                    )
                    for item in context
                ]
        except AppError:
            raise
        except SQLAlchemyError as exception:
            logger.warning("ai.history_unavailable", extra={"operation": "append-human"})
            raise AppError("AI 历史服务暂时不可用", status_code=503) from exception

    async def append_ai(
        self,
        user_id: str,
        role: ChatRole,
        *,
        content: str,
        reasoning: str | None,
    ) -> None:
        try:
            async with self._database.session() as session:
                async with session.begin():
                    thread_id = stable_thread_id(user_id, role)
                    position = await self._next_position(session, thread_id)
                    session.add(
                        AIChatMessage(
                            id=uuid.uuid4().hex,
                            thread_id=thread_id,
                            position=position,
                            role="ai",
                            content=content,
                            reasoning=reasoning or None,
                        )
                    )
                    await session.execute(
                        update(AIChatThread)
                        .where(AIChatThread.id == thread_id)
                        .values(updated_at=utc_now_naive())
                    )
        except SQLAlchemyError as exception:
            logger.warning("ai.history_unavailable", extra={"operation": "append-ai"})
            raise AppError("AI 历史服务暂时不可用", status_code=503) from exception

    async def list_messages(self, user_id: str, role: ChatRole) -> list[ConversationMessage]:
        try:
            async with self._database.session() as session:
                await self._ensure_user(session, user_id)
                thread_id = stable_thread_id(user_id, role)
                rows = list(
                    (
                        await session.execute(
                            select(AIChatMessage)
                            .where(AIChatMessage.thread_id == thread_id)
                            .order_by(AIChatMessage.position.desc())
                            .limit(self._message_limit)
                        )
                    ).scalars()
                )
                return [
                    ConversationMessage(
                        role=item.role,
                        content=item.content,
                        reasoning=item.reasoning,
                    )
                    for item in reversed(rows)
                ]
        except AppError:
            raise
        except SQLAlchemyError as exception:
            logger.warning("ai.history_unavailable", extra={"operation": "list"})
            raise AppError("AI 历史服务暂时不可用", status_code=503) from exception
