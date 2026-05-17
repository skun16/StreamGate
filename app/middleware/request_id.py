import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import app_logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    为每个 HTTP 请求生成 request_id。

    作用：
    1. 日志串联
    2. 前端排查问题
    3. 网关调用链追踪
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex

        # 放到 request.state，后续接口可以直接取
        request.state.request_id = request_id

        app_logger.info(
            {
                "event": "request_in",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )

        response = await call_next(request)

        # 响应头返回 request_id，方便前端或测试脚本定位
        response.headers["X-Request-Id"] = request_id

        app_logger.info(
            {
                "event": "request_out",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            }
        )

        return response