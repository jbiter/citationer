"""数据管理 Web 路由测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_status_returns_count(web_client: TestClient) -> None:
    response = web_client.get("/api/data/status")
    assert response.status_code == 200
    assert response.json()["total_records"] == 5
