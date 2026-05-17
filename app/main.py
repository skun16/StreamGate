import httpx
from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.core.config import settings


def create_app() -> FastAPI:
    """
    创建 StreamGate FastAPI 应用。

    main.py 的职责：
    1. 创建 FastAPI app
    2. 注册 API 路由
    3. 初始化全局 httpx.AsyncClient
    4. 关闭服务时释放 httpx.AsyncClient
    5. 提供健康检查接口
    """

    app = FastAPI(
        title=settings.APP_NAME,
        description="StreamGate: RAGFlow streaming gateway",
        version="0.1.0",
    )

    # 注册聊天接口
    app.include_router(chat_router)

    @app.on_event("startup")
    async def startup() -> None:
        """
        应用启动时创建全局 HTTP 异步客户端。

        不要每次请求都新建 AsyncClient。
        连接池复用对高并发流式服务很重要。
        """

        timeout = httpx.Timeout(
            connect=settings.RAGFLOW_CONNECT_TIMEOUT,
            read=settings.RAGFLOW_READ_TIMEOUT,
            write=settings.RAGFLOW_WRITE_TIMEOUT,
            pool=settings.RAGFLOW_POOL_TIMEOUT,
        )

        limits = httpx.Limits(
            max_connections=settings.HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=settings.HTTP_MAX_KEEPALIVE_CONNECTIONS,
            keepalive_expiry=30.0,
        )

        app.state.http_client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
        )

        print(f"{settings.APP_NAME} started")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        """
        应用关闭时释放 HTTP 客户端。
        """

        await app.state.http_client.aclose()

        print(f"{settings.APP_NAME} stopped")

    @app.get("/health")
    async def health():
        """
        健康检查接口。
        """

        return {
            "status": "ok",
            "app": settings.APP_NAME,
        }

    return app


app = create_app()