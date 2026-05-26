import time
from collections.abc import AsyncGenerator

import httpx
from fastapi import HTTPException, Request

from app.core.errors import StreamGateError
from app.core.limiter import limiter
from app.core.logger import app_logger
from app.core.sse import sse_event
from app.schemas.chat import ChatStreamRequest
from app.services.ragflow_client import RagflowClient
from app.services.user_service import get_user_group_from_request


async def stream_chat_events(
    request: Request,
    body: ChatStreamRequest,
) -> AsyncGenerator[str, None]:
    """
    生成 StreamGate 聊天接口的 SSE 事件流。
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
            is_new_session = body.session_id is None or not body.session_id.strip()

            yield sse_event({
                "type": "session",
                "request_id": request_id,
                "session_id": session_id,
                "session_create_time": round(session_create_time, 3),
                "is_new_session": is_new_session,
            })

            app_logger.info(
                {
                    "event": "session_ready",
                    "request_id": request_id,
                    "session_id": session_id,
                    "session_create_time": round(session_create_time, 3),
                    "is_new_session": is_new_session,
                }
            )

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
