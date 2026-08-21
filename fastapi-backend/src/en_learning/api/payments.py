from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from en_learning.api.dependencies import current_user, database_session
from en_learning.api.serialization import business_success
from en_learning.common.config import Settings
from en_learning.common.errors import AppError
from en_learning.db.models import (
    BackgroundJob,
    Course,
    CourseRecord,
    PaymentRecord,
    TradeStatus,
    User,
    utc_now_naive,
)
from en_learning.schemas.core import (
    CreatePaymentRequest,
    CreatePaymentResult,
    PaymentStatusResult,
)
from en_learning.schemas.envelope import SuccessEnvelope
from en_learning.services.alipay import AlipayGateway

logger = logging.getLogger("en_learning.api.payments")
router = APIRouter(prefix="/pay")
PAYMENT_SUCCESS_STATES = {TradeStatus.TRADE_SUCCESS, TradeStatus.TRADE_FINISHED}
PAYMENT_OPEN_STATES = {TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY}
REQUIRED_NOTIFICATION_FIELDS = {
    "app_id",
    "seller_id",
    "out_trade_no",
    "trade_no",
    "trade_status",
    "total_amount",
    "sign",
    "sign_type",
}


def _order_ref(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _money(value: Decimal | str) -> Decimal:
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exception:
        raise ValueError("invalid amount") from exception


def _payment_body(user_id: str, course_id: str) -> str:
    return json.dumps(
        {"courseId": course_id, "userId": user_id},
        ensure_ascii=False,
        separators=(",", ":"),
    )


async def _enqueue_job(request: Request, job_id: str) -> None:
    enqueue: Callable[[str], Awaitable[Any]] | None = getattr(
        request.app.state,
        "enqueue_background_job",
        None,
    )
    try:
        if enqueue is not None:
            await enqueue(job_id)
        else:
            from en_learning.worker.tasks import execute_background_job

            await execute_background_job.kiq(job_id)
    except Exception as exception:
        logger.warning(
            "payment.notification_enqueue_failed",
            extra={"jobRef": _order_ref(job_id), "failureType": type(exception).__name__},
        )


@router.post("/create", response_model=SuccessEnvelope[CreatePaymentResult])
async def create_payment(
    request: Request,
    payload: CreatePaymentRequest,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    settings: Settings = request.app.state.settings
    now = utc_now_naive()
    expires_at = now + timedelta(seconds=settings.payment_expiration_seconds)
    try:
        await session.scalar(select(User.id).where(User.id == user.id).with_for_update())
        course = await session.scalar(select(Course).where(Course.id == payload.course_id))
        if course is None:
            raise AppError("课程不存在", status_code=404)
        purchased = await session.scalar(
            select(CourseRecord.id).where(
                CourseRecord.user_id == user.id,
                CourseRecord.course_id == course.id,
                CourseRecord.is_purchased.is_(True),
            )
        )
        if purchased is not None:
            raise AppError("课程已购买", status_code=409)
        open_payment = await session.scalar(
            select(PaymentRecord)
            .where(
                PaymentRecord.user_id == user.id,
                PaymentRecord.course_id == course.id,
                PaymentRecord.trade_status.in_(PAYMENT_OPEN_STATES),
            )
            .order_by(PaymentRecord.created_at.desc())
            .with_for_update()
        )
        if open_payment is not None and (
            open_payment.expires_at is None or open_payment.expires_at > now
        ):
            raise AppError("存在待支付订单", status_code=409)
        if open_payment is not None:
            open_payment.trade_status = TradeStatus.TRADE_CLOSED

        out_trade_no = f"CJW-{uuid.uuid4().hex[:12].upper()}"
        amount = _money(course.price)
        payment = PaymentRecord(
            id=uuid.uuid4().hex,
            user_id=user.id,
            course_id=course.id,
            out_trade_no=out_trade_no,
            amount=amount,
            subject=course.name,
            body=course.description or "",
            expires_at=expires_at,
            app_id=settings.alipay_app_id,
            seller_id=settings.alipay_seller_id,
        )
        session.add(payment)
        await session.flush()
        pay_url = AlipayGateway(settings).page_pay_url(
            out_trade_no=out_trade_no,
            amount=f"{amount:.2f}",
            subject=course.name,
            body=_payment_body(user.id, course.id),
            expires_at=expires_at,
        )
        await session.commit()
    except AppError:
        await session.rollback()
        raise
    except (IntegrityError, SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.warning(
            "payment.create_failed",
            extra={"userRef": _order_ref(user.id), "failureType": type(exception).__name__},
        )
        raise AppError("支付服务暂时不可用", status_code=503) from exception
    except (TypeError, ValueError) as exception:
        await session.rollback()
        logger.error(
            "payment.configuration_invalid",
            extra={"failureType": type(exception).__name__},
        )
        raise AppError("支付服务暂时不可用", status_code=503) from exception
    time_expire = int(expires_at.replace(tzinfo=UTC).timestamp() * 1000)
    return business_success(
        request,
        {"payUrl": pay_url, "timeExpire": time_expire, "outTradeNo": out_trade_no},
    )


async def _notification_parameters(request: Request, max_bytes: int) -> dict[str, str]:
    if request.method == "GET":
        pairs = list(request.query_params.multi_items())
    else:
        content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
        if content_type != "application/x-www-form-urlencoded":
            raise ValueError("invalid content type")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise ValueError("notification too large")
        try:
            pairs = parse_qsl(
                bytes(body).decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=100,
            )
        except (UnicodeDecodeError, ValueError) as exception:
            raise ValueError("invalid notification form") from exception
    parameters: dict[str, str] = {}
    for key, value in pairs:
        if key in parameters or len(key) > 128 or len(value) > 4096:
            raise ValueError("ambiguous notification")
        parameters[key] = value
    if not REQUIRED_NOTIFICATION_FIELDS.issubset(parameters):
        raise ValueError("missing notification fields")
    return parameters


def _legacy_course_id(payment: PaymentRecord, parameters: dict[str, str]) -> str | None:
    if payment.course_id is not None:
        return payment.course_id
    try:
        legacy_body = json.loads(parameters.get("body", ""))
    except json.JSONDecodeError:
        return None
    if not isinstance(legacy_body, dict) or legacy_body.get("userId") != payment.user_id:
        return None
    course_id = legacy_body.get("courseId")
    return course_id if isinstance(course_id, str) and course_id else None


def _next_trade_status(current: TradeStatus, incoming: TradeStatus) -> TradeStatus | None:
    if incoming == current:
        return None
    if current == TradeStatus.TRADE_FINISHED:
        return None
    if current == TradeStatus.TRADE_SUCCESS:
        return incoming if incoming == TradeStatus.TRADE_FINISHED else None
    if current == TradeStatus.TRADE_CLOSED:
        if incoming in PAYMENT_SUCCESS_STATES:
            raise ValueError("closed order cannot become successful")
        return None
    if current in PAYMENT_OPEN_STATES:
        return incoming
    raise ValueError("unsupported transition")


async def _apply_notification(
    parameters: dict[str, str],
    settings: Settings,
    session: AsyncSession,
) -> tuple[str | None, str]:
    payment = await session.scalar(
        select(PaymentRecord)
        .where(PaymentRecord.out_trade_no == parameters["out_trade_no"])
        .with_for_update()
    )
    if payment is None:
        raise ValueError("unknown order")
    expected_app = payment.app_id or settings.alipay_app_id
    expected_seller = payment.seller_id or settings.alipay_seller_id
    if parameters["app_id"] != expected_app or parameters["seller_id"] != expected_seller:
        raise ValueError("merchant mismatch")
    if _money(parameters["total_amount"]) != _money(payment.amount):
        raise ValueError("amount mismatch")
    if payment.trade_no is not None and payment.trade_no != parameters["trade_no"]:
        raise ValueError("trade number mismatch")
    try:
        incoming = TradeStatus(parameters["trade_status"])
    except ValueError as exception:
        raise ValueError("unknown trade status") from exception
    next_status = _next_trade_status(payment.trade_status, incoming)
    if next_status is None:
        return None, payment.out_trade_no

    payment.trade_status = next_status
    payment.trade_no = parameters["trade_no"]
    payment.app_id = expected_app
    payment.seller_id = expected_seller
    gmt_payment = parameters.get("gmt_payment")
    if payment.send_pay_time is None and gmt_payment:
        try:
            payment.send_pay_time = datetime.strptime(gmt_payment, "%Y-%m-%d %H:%M:%S")
        except ValueError as exception:
            raise ValueError("invalid payment time") from exception

    if next_status not in PAYMENT_SUCCESS_STATES:
        return None, payment.out_trade_no
    course_id = _legacy_course_id(payment, parameters)
    if course_id is None:
        raise ValueError("order is not bound to a course")
    course = await session.scalar(select(Course).where(Course.id == course_id))
    if course is None or _money(course.price) != _money(payment.amount):
        raise ValueError("course facts mismatch")
    payment.course_id = course_id
    course_record = await session.scalar(
        select(CourseRecord).where(
            CourseRecord.user_id == payment.user_id,
            CourseRecord.course_id == course_id,
        )
    )
    if course_record is None:
        session.add(
            CourseRecord(
                id=uuid.uuid4().hex,
                user_id=payment.user_id,
                course_id=course_id,
                is_purchased=True,
                payment_record_id=payment.id,
            )
        )
    else:
        course_record.is_purchased = True
        if course_record.payment_record_id is None:
            course_record.payment_record_id = payment.id

    task_key = f"payment:{payment.id}:success"
    job = await session.scalar(select(BackgroundJob).where(BackgroundJob.task_key == task_key))
    if job is None:
        job = BackgroundJob(
            id=uuid.uuid4().hex,
            task_key=task_key,
            kind="PAYMENT_SUCCESS",
            status="PENDING",
            user_id=payment.user_id,
            payment_record_id=payment.id,
            payload={"courseId": course_id},
            max_attempts=settings.worker_job_max_attempts,
        )
        session.add(job)
    return job.id if job.status in {"PENDING", "FAILED"} else None, payment.out_trade_no


@router.api_route(
    "/notify",
    methods=["POST"],
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {"example": "success"}}}},
)
async def payment_notification(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> PlainTextResponse:
    settings: Settings = request.app.state.settings
    order_reference = "unknown"
    try:
        parameters = await _notification_parameters(request, settings.payment_notify_max_bytes)
        order_reference = _order_ref(parameters["out_trade_no"])
        if not AlipayGateway(settings).verify_notification(parameters):
            raise ValueError("invalid signature")
        job_id, _ = await _apply_notification(parameters, settings, session)
        await session.commit()
    except (ValueError, KeyError) as exception:
        await session.rollback()
        logger.warning(
            "payment.notification_rejected",
            extra={"orderRef": order_reference, "reason": str(exception)[:64]},
        )
        return PlainTextResponse("failure", status_code=400)
    except (IntegrityError, SQLAlchemyError, OSError) as exception:
        await session.rollback()
        logger.error(
            "payment.notification_database_failed",
            extra={"orderRef": order_reference, "failureType": type(exception).__name__},
        )
        return PlainTextResponse("failure", status_code=503)

    logger.info("payment.notification_committed", extra={"orderRef": order_reference})
    if job_id is not None:
        await _enqueue_job(request, job_id)
    return PlainTextResponse("success")


@router.get(
    "/status/{out_trade_no}",
    response_model=SuccessEnvelope[PaymentStatusResult],
)
async def payment_status(
    request: Request,
    out_trade_no: Annotated[str, Path(min_length=1, max_length=128)],
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> JSONResponse:
    try:
        payment = await session.scalar(
            select(PaymentRecord).where(
                PaymentRecord.out_trade_no == out_trade_no,
                PaymentRecord.user_id == user.id,
            )
        )
        if payment is None:
            raise AppError("订单不存在", status_code=404)
        is_purchased = False
        if payment.course_id is not None:
            is_purchased = bool(
                await session.scalar(
                    select(CourseRecord.id).where(
                        CourseRecord.course_id == payment.course_id,
                        CourseRecord.user_id == user.id,
                        CourseRecord.is_purchased.is_(True),
                    )
                )
            )
    except AppError:
        raise
    except (SQLAlchemyError, OSError) as exception:
        logger.warning("payment.status_failed", extra={"operation": "status"})
        raise AppError("数据库服务暂时不可用", status_code=503) from exception
    return business_success(
        request,
        {
            "outTradeNo": payment.out_trade_no,
            "tradeStatus": payment.trade_status.value,
            "isPurchased": is_purchased,
        },
    )
