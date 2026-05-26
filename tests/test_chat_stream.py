import json
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from app.main import create_app


class FakeRagflowClient:
    def __init__(self, client: object) -> None:
        self.client = client

    async def ensure_session(
        self,
        *,
        user_group: object,
        chat_type: object,
        session_id: str | None,
        session_name: str | None = None,
    ) -> str:
        return "new-session"

    async def stream_chat(
        self,
        *,
        user_group: object,
        chat_type: object,
        session_id: str,
        question: str,
    ) -> AsyncGenerator[dict, None]:
        yield {
            "type": "answer",
            "answer": "hello",
            "session_id": session_id,
            "message_id": "message-1",
        }
        yield {
            "type": "done",
        }


def parse_sse_events(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        assert block.startswith("data: ")
        events.append(json.loads(block[len("data: "):]))
    return events


def test_chat_stream_returns_ordered_sse_events(monkeypatch) -> None:
    import app.services.chat_stream_service as chat_stream_service

    monkeypatch.setattr(chat_stream_service, "RagflowClient", FakeRagflowClient)
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/chat/stream",
            headers={
                "X-User-Id": "office_test",
                "X-Request-Id": "request-1",
            },
            json={
                "chat_type": "kb",
                "question": "hello?",
            },
        )

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert [event["type"] for event in events] == ["start", "session", "answer", "done", "end"]
    assert events[0]["request_id"] == "request-1"
    assert events[1]["session_id"] == "new-session"
    assert events[1]["is_new_session"] is True
    assert events[2]["answer"] == "hello"
    assert events[2]["message_id"] == "message-1"
    assert all(event["request_id"] == "request-1" for event in events)
