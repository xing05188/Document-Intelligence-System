"""HTTP API 契约测试（TestClient）。"""
from __future__ import annotations


def test_health_returns_success_shape(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "status" in body["data"]
    assert "database_enabled" in body["data"]


def test_task_not_found_error_shape(api_client):
    r = api_client.get("/tasks/__nonexistent_task_id__")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]


def test_openapi_available(api_client):
    r = api_client.get("/openapi.json")
    assert r.status_code == 200
    assert "openapi" in r.json()
