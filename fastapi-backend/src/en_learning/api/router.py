from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from en_learning.api.courses import router as course_router
from en_learning.api.learning import router as learning_router
from en_learning.api.payments import router as payment_router
from en_learning.api.tracker import router as tracker_router
from en_learning.api.users import router as user_router
from en_learning.api.word_books import router as word_book_router
from en_learning.common.responses import success_response
from en_learning.schemas.envelope import SuccessEnvelope

router = APIRouter(prefix="/api/v1", tags=["core-api"])


@router.get("/", response_model=SuccessEnvelope[None])
async def root(request: Request) -> JSONResponse:
    return success_response(request, None, message="请求成功", code=200)


router.include_router(user_router)
router.include_router(course_router)
router.include_router(word_book_router)
router.include_router(learning_router)
router.include_router(payment_router)
router.include_router(tracker_router)
