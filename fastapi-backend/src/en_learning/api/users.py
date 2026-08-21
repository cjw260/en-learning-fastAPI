from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from email import policy
from email.parser import BytesParser
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import core_resources, current_user, database_session
from en_learning.api.serialization import business_success, token_data, user_data, user_update_data
from en_learning.common.auth import decode_token, encode_token
from en_learning.common.config import Settings
from en_learning.common.errors import AppError
from en_learning.db.models import User, utc_now_naive
from en_learning.schemas.core import (
    AvatarResult,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPair,
    UserUpdateRequest,
    UserUpdateResult,
    UserWithToken,
)
from en_learning.schemas.envelope import SuccessEnvelope
from en_learning.services.passwords import hash_password, verify_password

logger = logging.getLogger("en_learning.api.users")
router = APIRouter(prefix="/user")

IMAGE_TYPES: dict[str, tuple[str, Callable[[bytes], bool]]] = {
    "image/png": ("png", lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/jpeg": ("jpg", lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/webp": (
        "webp",
        lambda content: (
            len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        ),
    ),
}
ALLOWED_SUFFIXES = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
}


def _issue_tokens(settings: Settings, user: User) -> dict[str, str]:
    return token_data(
        encode_token(
            settings,
            user_id=user.id,
            name=user.name,
            email=user.email,
            token_type="access",
            refresh_version=user.refresh_token_version,
        ),
        encode_token(
            settings,
            user_id=user.id,
            name=user.name,
            email=user.email,
            token_type="refresh",
            refresh_version=user.refresh_token_version,
        ),
    )


@router.post("/login", response_model=SuccessEnvelope[UserWithToken])
async def login(
    request: Request,
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    try:
        async with session.begin():
            user = await session.scalar(
                select(User).where(User.phone == payload.phone).with_for_update()
            )
            if user is None:
                await asyncio.to_thread(hash_password, payload.password)
                raise AppError("手机号或密码不正确", status_code=401)
            password_check = await asyncio.to_thread(
                verify_password,
                payload.password,
                user.password,
            )
            if not password_check.valid:
                raise AppError("手机号或密码不正确", status_code=401)
            if password_check.needs_upgrade:
                user.password = await asyncio.to_thread(hash_password, payload.password)
            user.last_login_at = utc_now_naive()
            user.refresh_token_version += 1
            await session.flush()
            result = {**user_data(user), "token": _issue_tokens(request.app.state.settings, user)}
        return business_success(request, result)
    except AppError:
        raise
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("user.database_unavailable", extra={"operation": "login"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception


@router.post("/register", response_model=SuccessEnvelope[UserWithToken])
async def register(
    request: Request,
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    password = await asyncio.to_thread(hash_password, payload.password)
    user = User(
        id=uuid.uuid4().hex,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        password=password,
        last_login_at=utc_now_naive(),
        refresh_token_version=1,
    )
    try:
        async with session.begin():
            session.add(user)
            await session.flush()
            result = {**user_data(user), "token": _issue_tokens(request.app.state.settings, user)}
        return business_success(request, result)
    except IntegrityError as exception:
        raise AppError("手机号或邮箱已经存在", status_code=409) from exception
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("user.database_unavailable", extra={"operation": "register"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception


@router.post("/refresh-token", response_model=SuccessEnvelope[TokenPair])
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    settings: Settings = request.app.state.settings
    try:
        claims = decode_token(payload.refresh_token, settings, expected_type="refresh")
    except ValueError as exception:
        raise AppError("refreshToken已过期或无效", status_code=401) from exception
    try:
        async with session.begin():
            user = await session.scalar(
                select(User).where(User.id == claims.user_id).with_for_update()
            )
            if user is None or user.refresh_token_version != claims.refresh_version:
                raise AppError("refreshToken已过期或无效", status_code=401)
            user.refresh_token_version += 1
            await session.flush()
            result = _issue_tokens(settings, user)
        return business_success(request, result)
    except AppError:
        raise
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("user.database_unavailable", extra={"operation": "refresh"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception


@router.post("/update-user", response_model=SuccessEnvelope[UserUpdateResult])
async def update_user(
    request: Request,
    payload: UserUpdateRequest,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    user.name = payload.name
    user.email = payload.email
    user.address = payload.address
    user.avatar = payload.avatar
    user.bio = payload.bio
    if payload.is_timing_task is not None:
        user.is_timing_task = payload.is_timing_task
    if payload.timing_task_time is not None:
        user.timing_task_time = payload.timing_task_time
    try:
        await session.commit()
        return business_success(request, user_update_data(user))
    except IntegrityError as exception:
        await session.rollback()
        raise AppError("邮箱已经存在", status_code=409) from exception
    except (SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning("user.database_unavailable", extra={"operation": "update"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception


def _avatar_type(filename: str, content_type: str, content: bytes) -> tuple[str, str]:
    content_type = content_type.lower()
    definition = IMAGE_TYPES.get(content_type)
    suffix = PurePath(filename).suffix.lower()
    if definition is None or suffix not in ALLOWED_SUFFIXES.get(content_type, set()):
        raise AppError("仅支持 PNG、JPEG 或 WebP 图片", status_code=422)
    extension, matches = definition
    if not matches(content):
        raise AppError("图片内容与文件类型不匹配", status_code=422)
    return extension, content_type


async def _multipart_avatar(request: Request) -> tuple[str, str, bytes]:
    content_type = request.headers.get("content-type", "")
    if len(content_type) > 512 or not content_type.lower().startswith("multipart/form-data;"):
        raise AppError("必须使用 multipart/form-data 上传", status_code=422)
    body = await request.body()
    try:
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: "
            + content_type.encode("ascii")
            + b"\r\nMIME-Version: 1.0\r\n\r\n"
            + body
        )
    except (UnicodeEncodeError, ValueError) as exception:
        raise AppError("multipart 文件格式无效", status_code=422) from exception
    if not message.is_multipart():
        raise AppError("multipart 文件格式无效", status_code=422)
    parts = list(message.iter_parts())
    file_parts = [
        part
        for part in parts
        if part.get_content_disposition() == "form-data"
        and part.get_param("name", header="content-disposition") == "file"
    ]
    if len(parts) != 1 or len(file_parts) != 1:
        raise AppError("必须且只能上传一个 file 字段", status_code=422)
    part = file_parts[0]
    filename = part.get_filename() or ""
    payload = part.get_payload(decode=True)
    if not filename or not isinstance(payload, bytes):
        raise AppError("文件不存在", status_code=422)
    return filename, part.get_content_type(), payload


@router.post(
    "/upload-avatar",
    response_model=SuccessEnvelope[AvatarResult],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["file"],
                        "properties": {"file": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
async def upload_avatar(
    request: Request,
    user: Annotated[User, Depends(current_user)],
) -> JSONResponse:
    settings: Settings = request.app.state.settings
    filename, content_type, content = await _multipart_avatar(request)
    if not content:
        raise AppError("文件不存在", status_code=422)
    if len(content) > settings.avatar_max_bytes:
        raise AppError("文件大小不能超过5MB", status_code=413)
    extension, content_type = _avatar_type(filename, content_type, content)
    object_id = uuid.uuid4().hex
    object_name = f"users/{user.id}/{object_id}.{extension}"
    storage = core_resources(request).object_storage
    try:
        stored = await storage.put_avatar(
            user_id=user.id,
            object_id=object_id,
            extension=extension,
            content_type=content_type,
            content=content,
        )
    except Exception as exception:
        try:
            await storage.remove(object_name)
        except Exception:
            logger.warning("avatar.cleanup_failed", extra={"userRef": user.id[:8]})
        logger.warning("avatar.upload_failed", extra={"userRef": user.id[:8]})
        raise AppError("头像存储服务暂时不可用", status_code=503) from exception
    return business_success(
        request,
        {"previewUrl": stored.preview_url, "databaseUrl": stored.database_url},
    )
