import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas.chat import ChatStreamRequest
from app.services.ragflow_client import RagflowClient
from app.services.user_service import get_user_group_from_request


router = APIRouter(prefix="/api/chat", tags=["chat"])


# 全局并发限制
global_semaphore = asyncio.Semaphore(settings.GLOBAL_CONCURRENCY)

# RAGFlow 并发限制
ragflow_semaphore = asyncio.Semaphore(settings.RAGFLOW_CONCURRENCY)


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

    request_id = uuid.uuid4().hex
    start_time = time.perf_counter()

    yield sse_event({
        "type": "start",
        "request_id": request_id,
    })

    try:
        # 1. 后端识别用户分组
        user_group = get_user_group_from_request(request)

        async with global_semaphore:
            async with ragflow_semaphore:
                # 2. 创建 RAGFlow 客户端
                ragflow_client = RagflowClient(request.app.state.http_client)

                # 3. 确保 session 存在：如果前端没传 session_id，就自动创建
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

                # 5. 调用 RAGFlow 流式问答
                async for event in ragflow_client.stream_chat(
                    user_group=user_group,
                    chat_type=body.chat_type,
                    session_id=session_id,
                    question=body.question,
                ):
                    if await request.is_disconnected():
                        print(f"[{request_id}] client disconnected")
                        return

                    event["request_id"] = request_id
                    yield sse_event(event)

    except HTTPException as e:
        yield sse_event({
            "type": "error",
            "request_id": request_id,
            "status_code": e.status_code,
            "message": e.detail,
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

        yield sse_event({
            "type": "end",
            "request_id": request_id,
            "total_time": round(total_time, 3),
        })

        yield "data: [DONE]\n\n"


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