from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from en_learning.ai.prompts import ROLE_PROMPTS
from en_learning.ai.service import ChatService
from en_learning.common.auth import Principal, get_current_principal
from en_learning.common.config import Settings
from en_learning.common.responses import success_response
from en_learning.schemas.chat import ChatRequest, ChatRole, HistoryMessage, PromptMode
from en_learning.schemas.envelope import SuccessEnvelope
from en_learning.services.resources import AIResources

router = APIRouter(prefix="/ai/v1", tags=["ai-api"])


@router.get("/", response_model=SuccessEnvelope[None])
async def root(request: Request) -> JSONResponse:
    return success_response(request, None, message="请求成功", code=200)


def service_for(request: Request) -> ChatService:
    settings = cast(Settings, request.app.state.settings)
    resources = cast(AIResources, request.app.state.resources)
    return ChatService(settings, resources)


@router.get("/prompt/list", response_model=SuccessEnvelope[list[PromptMode]])
async def prompt_list(
    request: Request,
    _principal: Annotated[Principal, Depends(get_current_principal)],
) -> JSONResponse:
    return success_response(
        request,
        [item.mode.model_dump(mode="json") for item in ROLE_PROMPTS],
    )


@router.post("/chat")
async def chat(
    request: Request,
    payload: ChatRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> StreamingResponse:
    service = service_for(request)
    prepared = await service.prepare(payload, principal)
    return StreamingResponse(
        service.stream(request, prepared),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history", response_model=SuccessEnvelope[list[HistoryMessage]])
async def chat_history(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    user_id: Annotated[str, Query(alias="userId", min_length=1, max_length=128)],
    role: ChatRole,
) -> JSONResponse:
    history = await service_for(request).history(user_id, role, principal)
    return success_response(request, history)
