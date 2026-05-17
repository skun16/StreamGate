import json
import time
import uuid
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas.chat import ChatStreamRequest, CreateSessionRequest
from app.services.ragflow_client import RagflowClient
from app.services.user_service import get_user_group_from_request
from app.core.logger import app_logger
from app.core.limiter import limiter
from app.schemas.common import success_response
from app.core.errors import StreamGateError, to_http_exception


router = APIRouter(prefix="/api/chat", tags=["chat"])


def sse_event(data: dict) -> str:
    """
    将 dict 转成 SSE 格式。
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_generator(
    request: Request,
    body: ChatStreamRequest,
) -> AsyncGenerator[str, None]:
    """
    生成 SSE 流式输出。
    """

    request_id = request.state.request_id
    start_time = time.perf_counter()
    first_answer_time = None
    answer_event_count = 0
    
    yield sse_event({
        "type": "start",
        "request_id": request_id,
    })
    
    app_logger.info(
        {
            "event": "stream_start",
            "request_id": request_id,
            "chat_type": body.chat_type,
            "has_session_id": bool(body.session_id),
            "question_length": len(body.question),
        }
    )

    try:
        # 1. 后端识别用户分组
        user_group = get_user_group_from_request(request)
        app_logger.info(
            {
                "event": "user_group_resolved",
                "request_id": request_id,
                "user_group": user_group,
            }
        )
        async with limiter.limit(request_id):
            ragflow_client = RagflowClient(request.app.state.http_client)

            session_start = time.perf_counter()

            session_id = await ragflow_client.ensure_session(
                user_group=user_group,
                chat_type=body.chat_type,
                session_id=body.session_id,
                session_name=body.session_name,
            )

            session_create_time = time.perf_counter() - session_start

            yield sse_event({
                "type": "session",
                "request_id": request_id,
                "session_id": session_id,
                "session_create_time": round(session_create_time, 3),
                "is_new_session": body.session_id is None or not body.session_id.strip(),
            })
            
            app_logger.info(
                {
                    "event": "session_ready",
                    "request_id": request_id,
                    "session_id": session_id,
                    "session_create_time": round(session_create_time, 3),
                    "is_new_session": body.session_id is None or not body.session_id.strip(),
                }
            )

            # 5. 调用 RAGFlow 流式问答
            async for event in ragflow_client.stream_chat(
                user_group=user_group,
                chat_type=body.chat_type,
                session_id=session_id,
                question=body.question,
            ):
                if await request.is_disconnected():
                    app_logger.warning(
                        {
                            "event": "client_disconnected",
                            "request_id": request_id,
                            "session_id": session_id,
                        }
                    )
                    return

                if event.get("type") == "answer":
                    answer_event_count += 1

                    if first_answer_time is None:
                        first_answer_time = time.perf_counter()
                        app_logger.info(
                            {
                                "event": "first_answer",
                                "request_id": request_id,
                                "ttft": round(first_answer_time - start_time, 3),
                            }
                        )

                event["request_id"] = request_id
                yield sse_event(event)

    except HTTPException as e:
        app_logger.warning(
            {
                "event": "stream_http_exception",
                "request_id": request_id,
                "status_code": e.status_code,
                "message": e.detail,
            }
        )

        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "status_code": e.status_code,
            "message": e.detail,
        })

    except StreamGateError as e:
        app_logger.warning(
            {
                "event": "stream_business_error",
                "request_id": request_id,
                "error": e.to_dict(),
            }
        )

        yield sse_event({
            "type": "error",
            "request_id": request_id,
            **e.to_dict(),
        })

    except httpx.ConnectTimeout:
        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "message": "连接 RAGFlow 超时",
        })

    except httpx.ReadTimeout:
        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "message": "RAGFlow 长时间没有返回内容，读取超时",
        })

    except httpx.RemoteProtocolError as e:
        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "message": "RAGFlow 流式连接异常中断",
            "detail": str(e),
        })

    except Exception as e:
        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "message": "网关内部错误",
            "detail": str(e),
        })

    finally:
        total_time = time.perf_counter() - start_time

        app_logger.info(
            {
                "event": "stream_end",
                "request_id": request_id,
                "total_time": round(total_time, 3),
                "answer_event_count": answer_event_count,
                "has_first_answer": first_answer_time is not None,
            }
        )

        yield sse_event({
            "type": "end",
            "request_id": request_id,
            "total_time": round(total_time, 3),
        })


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
        stream_generator(request, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )