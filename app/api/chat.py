import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatStreamRequest, CreateSessionRequest
from app.services.ragflow_client import RagflowClient
from app.services.user_service import get_user_group_from_request
from app.core.logger import app_logger
from app.schemas.common import success_response
from app.core.errors import StreamGateError, to_http_exception
from app.services.chat_stream_service import stream_chat_events


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/session")
async def create_chat_session(request: Request, body: CreateSessionRequest):
    """
    创建 RAGFlow 会话。
    """

    request_id = request.state.request_id
    start_time = time.perf_counter()

    try:
        user_group = get_user_group_from_request(request)

        app_logger.info(
            {
                "event": "create_session_start",
                "request_id": request_id,
                "user_group": user_group,
                "chat_type": body.chat_type,
                "session_name": body.session_name,
            }
        )

        ragflow_client = RagflowClient(request.app.state.http_client)

        session_id = await ragflow_client.create_session(
            user_group=user_group,
            chat_type=body.chat_type,
            session_name=body.session_name,
        )

        elapsed = time.perf_counter() - start_time

        app_logger.info(
            {
                "event": "create_session_success",
                "request_id": request_id,
                "user_group": user_group,
                "chat_type": body.chat_type,
                "session_id": session_id,
                "elapsed": round(elapsed, 3),
            }
        )

        return success_response(
            data={
                "request_id": request_id,
                "session_id": session_id,
                "chat_type": body.chat_type,
                "session_create_time": round(elapsed, 3),
            }
        )

    except HTTPException:
        raise
    except StreamGateError as e:
        elapsed = time.perf_counter() - start_time

        app_logger.warning(
            {
                "event": "create_session_business_error",
                "request_id": request_id,
                "elapsed": round(elapsed, 3),
                "error": e.to_dict(),
            }
        )

        raise to_http_exception(e)
    except Exception as e:
        elapsed = time.perf_counter() - start_time

        app_logger.exception(
            {
                "event": "create_session_failed",
                "request_id": request_id,
                "chat_type": body.chat_type,
                "elapsed": round(elapsed, 3),
                "error": str(e),
            }
        )

        raise HTTPException(
            status_code=500,
            detail={
                "request_id": request_id,
                "message": "创建会话失败",
                "error": str(e),
            },
        )

@router.post("/stream")
async def chat_stream(request: Request, body: ChatStreamRequest):
    """
    StreamGate 流式聊天接口。
    """

    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question 不能为空")

    return StreamingResponse(
        stream_chat_events(request, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
