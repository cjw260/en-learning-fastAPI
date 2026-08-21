from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from en_learning.common.responses import success_response
from en_learning.schemas.envelope import SuccessEnvelope

router = APIRouter(prefix="/ai/v1", tags=["ai-api"])


@router.get("/", response_model=SuccessEnvelope[None])
async def root(request: Request) -> JSONResponse:
    return success_response(request, None, message="请求成功", code=200)
