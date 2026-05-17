from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChatType(str, Enum):
    """
    Chat 功能类型。
    """

    KB = "kb"
    SUMMARY = "summary"


class ChatStreamRequest(BaseModel):
    """
    前端请求 StreamGate 流式问答接口时传入的参数。
    """

    chat_type: ChatType = Field(
        ...,
        description="Chat 类型：kb=知识库问答，summary=文件总结",
    )

    question: str = Field(
        ...,
        min_length=1,
        description="用户问题",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="RAGFlow 会话 ID；新建对话时可不传",
    )

    session_name: Optional[str] = Field(
        default=None,
        description="新建 RAGFlow 会话时使用的名称",
    )