from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    StreamGate 普通 JSON 接口的统一响应结构。

    注意：
    流式接口 /api/chat/stream 返回的是 SSE，不使用这个结构。
    普通接口，例如 /api/chat/session，可以使用这个结构。
    """

    code: int = Field(
        default=0,
        description="业务状态码，0 表示成功",
    )

    message: str = Field(
        default="",
        description="响应消息",
    )

    data: Optional[T] = Field(
        default=None,
        description="响应数据",
    )


def success_response(
    data: Any = None,
    message: str = "",
    code: int = 0,
) -> dict:
    """
    构造成功响应。
    """

    return {
        "code": code,
        "message": message,
        "data": data,
    }


def error_response(
    message: str,
    code: int = 500,
    data: Any = None,
) -> dict:
    """
    构造错误响应。

    注意：
    FastAPI 的 HTTPException 仍然负责 HTTP 状态码；
    这里的 code 是业务错误码。
    """

    return {
        "code": code,
        "message": message,
        "data": data,
    }