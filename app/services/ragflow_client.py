import json
from collections.abc import AsyncGenerator
from typing import Optional

import httpx

from app.core.config import settings
from app.schemas.chat import ChatType
from app.services.user_service import UserGroup
from app.core.errors import RagflowError


class RagflowClient:
    """
    RAGFlow 客户端。

    负责：
    1. 根据用户分组和功能类型选择 chat_id
    2. 创建 RAGFlow session
    3. 调用 RAGFlow 官方流式 completions 接口
    4. 将 RAGFlow 原始 answer 透传给上层
    """

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def get_chat_id(self, user_group: UserGroup, chat_type: ChatType) -> str:
        """
        根据用户分组和功能类型选择对应的 RAGFlow Chat ID。
        """

        if user_group == UserGroup.OFFICE_LEADER and chat_type == ChatType.KB:
            return settings.RAGFLOW_OFFICE_LEADER_KB_CHAT_ID

        if user_group == UserGroup.OFFICE_LEADER and chat_type == ChatType.SUMMARY:
            return settings.RAGFLOW_OFFICE_LEADER_SUMMARY_CHAT_ID

        if user_group == UserGroup.DEPARTMENT_LEADER and chat_type == ChatType.KB:
            return settings.RAGFLOW_DEPARTMENT_LEADER_KB_CHAT_ID

        if user_group == UserGroup.DEPARTMENT_LEADER and chat_type == ChatType.SUMMARY:
            return settings.RAGFLOW_DEPARTMENT_LEADER_SUMMARY_CHAT_ID

        raise ValueError(f"不支持的用户分组或 Chat 类型: {user_group=}, {chat_type=}")

    def build_headers(self) -> dict:
        """
        构造 RAGFlow 请求头。
        """

        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}",
        }

    def build_session_url(self, chat_id: str) -> str:
        """
        拼接创建 session 的接口地址。

        POST /api/v1/chats/{chat_id}/sessions
        """

        base_url = settings.RAGFLOW_BASE_URL.rstrip("/")
        return f"{base_url}/api/v1/chats/{chat_id}/sessions"

    def build_completion_url(self, chat_id: str) -> str:
        """
        拼接流式问答接口地址。

        POST /api/v1/chats/{chat_id}/completions
        """

        base_url = settings.RAGFLOW_BASE_URL.rstrip("/")
        return f"{base_url}/api/v1/chats/{chat_id}/completions"

    async def create_session(
        self,
        *,
        user_group: UserGroup,
        chat_type: ChatType,
        session_name: Optional[str] = None,
    ) -> str:
        """
        创建 RAGFlow session，并返回 session_id。
        """

        chat_id = self.get_chat_id(user_group=user_group, chat_type=chat_type)

        url = self.build_session_url(chat_id)
        headers = self.build_headers()

        payload = {
            "name": session_name or "new session",
        }

        response = await self.client.post(
            url,
            headers=headers,
            json=payload,
        )

        response_text = response.text

        if response.status_code != 200:
            raise RagflowError(
                message="RAGFlow 创建 session 失败",
                data={
                    "status_code": response.status_code,
                    "body": response_text[:500],
                    "url": url,
                },
            )

        try:
            obj = response.json()
        except Exception as exc:
            raise RagflowError(
                message="RAGFlow 创建 session 返回非 JSON",
                data={
                    "status_code": response.status_code,
                    "body": response_text[:500],
                    "url": url,
                },
            ) from exc

        if obj.get("code") != 0:
            raise RagflowError(
                message="RAGFlow 创建 session 返回业务失败",
                data=obj,
            )

        data = obj.get("data") or {}
        session_id = data.get("id")

        if not session_id:
            raise RagflowError(
                message="RAGFlow 创建 session 成功但未返回 session_id",
                data=obj,
            )

        return session_id

    async def ensure_session(
        self,
        *,
        user_group: UserGroup,
        chat_type: ChatType,
        session_id: Optional[str],
        session_name: Optional[str] = None,
    ) -> str:
        """
        如果前端传了 session_id，就直接使用。
        如果没传，就先创建一个新的 session。
        """

        if session_id and session_id.strip():
            return session_id.strip()

        return await self.create_session(
            user_group=user_group,
            chat_type=chat_type,
            session_name=session_name,
        )

    async def stream_chat(
        self,
        *,
        user_group: UserGroup,
        chat_type: ChatType,
        session_id: str,
        question: str,
    ) -> AsyncGenerator[dict, None]:
        """
        调用 RAGFlow 流式问答接口。

        注意：
        这里不做 answer 差分。
        RAGFlow 返回什么 answer，就向上层返回什么 answer。
        """

        chat_id = self.get_chat_id(user_group=user_group, chat_type=chat_type)

        url = self.build_completion_url(chat_id)
        headers = self.build_headers()

        payload = {
            "question": question,
            "stream": True,
            "session_id": session_id,
        }

        async with self.client.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                raise RagflowError(
                    message="RAGFlow 问答请求失败",
                    data={
                        "status_code": response.status_code,
                        "body": error_body.decode("utf-8", errors="ignore")[:500],
                    },
                )

            async for line in response.aiter_lines():
                line = line.strip()

                if not line:
                    continue

                if line.startswith("data:"):
                    line = line[len("data:"):].strip()

                if not line:
                    continue

                obj = self.parse_json_line(line)

                if obj.get("data") is True:
                    yield {
                        "type": "done",
                    }
                    break

                data = obj.get("data")

                if not isinstance(data, dict):
                    continue

                answer = data.get("answer")
                reference = data.get("reference")
                message_id = data.get("id")
                returned_session_id = data.get("session_id")

                if isinstance(answer, str):
                    yield {
                        "type": "answer",
                        "answer": answer,
                        "session_id": returned_session_id,
                        "message_id": message_id,
                    }

                if isinstance(reference, dict) and reference:
                    yield {
                        "type": "reference",
                        "reference": reference,
                    }

    def parse_json_line(self, line: str) -> dict:
        """
        解析 RAGFlow 返回的单行 JSON。
        """

        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise RagflowError(
                message="RAGFlow 返回了非 JSON 流式数据",
                data={
                    "line": line[:300],
                },
            ) from exc