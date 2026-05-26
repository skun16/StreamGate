from fastapi.testclient import TestClient

from app.main import create_app


def test_ragflow_diagnostics_returns_safe_configuration_summary() -> None:
    client = TestClient(create_app())

    response = client.get("/diagnostics/ragflow")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "ragflow": {
            "base_url": "http://ragflow.local",
            "api_key_configured": True,
            "chat_mappings": {
                "office_leader": {
                    "kb": True,
                    "summary": True,
                },
                "department_leader": {
                    "kb": True,
                    "summary": True,
                },
            },
        },
        "timeouts": {
            "connect": 1.5,
            "read": 30.0,
            "write": 2.5,
            "pool": 3.5,
        },
        "limits": {
            "http_max_connections": 20,
            "http_max_keepalive_connections": 5,
            "global_concurrency": 10,
            "ragflow_concurrency": 4,
        },
    }


def test_ragflow_diagnostics_does_not_expose_secrets_or_chat_ids() -> None:
    client = TestClient(create_app())

    response = client.get("/diagnostics/ragflow")

    body = response.text
    assert "secret-test-key" not in body
    assert "office-kb" not in body
    assert "office-summary" not in body
    assert "department-kb" not in body
    assert "department-summary" not in body
