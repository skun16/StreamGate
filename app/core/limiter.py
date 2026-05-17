import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.core.logger import app_logger


class ConcurrencyLimiter:
    """
    StreamGate 并发限制器。

    当前提供两层限制：
    1. global_semaphore：限制 StreamGate 整体并发
    2. ragflow_semaphore：限制同时打到 RAGFlow 的并发
    """

    def __init__(self) -> None:
        self.global_semaphore = asyncio.Semaphore(settings.GLOBAL_CONCURRENCY)
        self.ragflow_semaphore = asyncio.Semaphore(settings.RAGFLOW_CONCURRENCY)

    @asynccontextmanager
    async def limit(self, request_id: str) -> AsyncGenerator[None, None]:
        """
        同时获取全局并发许可和 RAGFlow 并发许可。

        用法：

        async with limiter.limit(request_id):
            ...
        """

        app_logger.info(
            {
                "event": "limiter_waiting",
                "request_id": request_id,
                "global_limit": settings.GLOBAL_CONCURRENCY,
                "ragflow_limit": settings.RAGFLOW_CONCURRENCY,
            }
        )

        async with self.global_semaphore:
            async with self.ragflow_semaphore:
                app_logger.info(
                    {
                        "event": "limiter_acquired",
                        "request_id": request_id,
                    }
                )

                try:
                    yield

                finally:
                    app_logger.info(
                        {
                            "event": "limiter_released",
                            "request_id": request_id,
                        }
                    )


limiter = ConcurrencyLimiter()