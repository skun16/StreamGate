import asyncio

import pytest

from app.core.errors import RagflowError
from app.schemas.chat import ChatType
from app.services.ragflow_client import RagflowClient
from app.services.user_service import UserGroup


def test_get_chat_id_selects_mapping_for_user_group_and_chat_type() -> None:
    client = RagflowClient(client=None)  # type: ignore[arg-type]

    assert client.get_chat_id(UserGroup.OFFICE_LEADER, ChatType.KB) == "office-kb"
    assert client.get_chat_id(UserGroup.OFFICE_LEADER, ChatType.SUMMARY) == "office-summary"
    assert client.get_chat_id(UserGroup.DEPARTMENT_LEADER, ChatType.KB) == "department-kb"
    assert client.get_chat_id(UserGroup.DEPARTMENT_LEADER, ChatType.SUMMARY) == "department-summary"


def test_parse_json_line_returns_decoded_object() -> None:
    client = RagflowClient(client=None)  # type: ignore[arg-type]

    assert client.parse_json_line('{"data":{"answer":"hello"}}') == {
        "data": {
            "answer": "hello",
        },
    }


def test_parse_json_line_raises_ragflow_error_for_invalid_json() -> None:
    client = RagflowClient(client=None)  # type: ignore[arg-type]

    with pytest.raises(RagflowError) as exc_info:
        client.parse_json_line("not-json")

    assert exc_info.value.message == "RAGFlow 返回了非 JSON 流式数据"
    assert exc_info.value.data == {"line": "not-json"}


def test_ensure_session_reuses_existing_session_id() -> None:
    client = RagflowClient(client=None)  # type: ignore[arg-type]

    session_id = asyncio.run(
        client.ensure_session(
            user_group=UserGroup.OFFICE_LEADER,
            chat_type=ChatType.KB,
            session_id="  existing-session  ",
        )
    )

    assert session_id == "existing-session"
