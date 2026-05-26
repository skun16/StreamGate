from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/ragflow")
async def ragflow_diagnostics() -> dict:
    """
    返回 RAGFlow 相关配置的安全诊断摘要。
    """

    return {
        "status": "ok",
        "ragflow": {
            "base_url": settings.RAGFLOW_BASE_URL,
            "api_key_configured": bool(settings.RAGFLOW_API_KEY.strip()),
            "chat_mappings": {
                "office_leader": {
                    "kb": bool(settings.RAGFLOW_OFFICE_LEADER_KB_CHAT_ID.strip()),
                    "summary": bool(settings.RAGFLOW_OFFICE_LEADER_SUMMARY_CHAT_ID.strip()),
                },
                "department_leader": {
                    "kb": bool(settings.RAGFLOW_DEPARTMENT_LEADER_KB_CHAT_ID.strip()),
                    "summary": bool(settings.RAGFLOW_DEPARTMENT_LEADER_SUMMARY_CHAT_ID.strip()),
                },
            },
        },
        "timeouts": {
            "connect": settings.RAGFLOW_CONNECT_TIMEOUT,
            "read": settings.RAGFLOW_READ_TIMEOUT,
            "write": settings.RAGFLOW_WRITE_TIMEOUT,
            "pool": settings.RAGFLOW_POOL_TIMEOUT,
        },
        "limits": {
            "http_max_connections": settings.HTTP_MAX_CONNECTIONS,
            "http_max_keepalive_connections": settings.HTTP_MAX_KEEPALIVE_CONNECTIONS,
            "global_concurrency": settings.GLOBAL_CONCURRENCY,
            "ragflow_concurrency": settings.RAGFLOW_CONCURRENCY,
        },
    }
