import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


@pytest.fixture(autouse=True)
def stable_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "APP_NAME", "StreamGate")
    monkeypatch.setattr(settings, "RAGFLOW_BASE_URL", "http://ragflow.local")
    monkeypatch.setattr(settings, "RAGFLOW_API_KEY", "secret-test-key")
    monkeypatch.setattr(settings, "RAGFLOW_OFFICE_LEADER_KB_CHAT_ID", "office-kb")
    monkeypatch.setattr(settings, "RAGFLOW_OFFICE_LEADER_SUMMARY_CHAT_ID", "office-summary")
    monkeypatch.setattr(settings, "RAGFLOW_DEPARTMENT_LEADER_KB_CHAT_ID", "department-kb")
    monkeypatch.setattr(settings, "RAGFLOW_DEPARTMENT_LEADER_SUMMARY_CHAT_ID", "department-summary")
    monkeypatch.setattr(settings, "RAGFLOW_CONNECT_TIMEOUT", 1.5)
    monkeypatch.setattr(settings, "RAGFLOW_READ_TIMEOUT", 30.0)
    monkeypatch.setattr(settings, "RAGFLOW_WRITE_TIMEOUT", 2.5)
    monkeypatch.setattr(settings, "RAGFLOW_POOL_TIMEOUT", 3.5)
    monkeypatch.setattr(settings, "HTTP_MAX_CONNECTIONS", 20)
    monkeypatch.setattr(settings, "HTTP_MAX_KEEPALIVE_CONNECTIONS", 5)
    monkeypatch.setattr(settings, "GLOBAL_CONCURRENCY", 10)
    monkeypatch.setattr(settings, "RAGFLOW_CONCURRENCY", 4)
    yield
