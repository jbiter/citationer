"""静态仪表板前端测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_dashboard_index_loads(empty_client: TestClient) -> None:
    response = empty_client.get("/")
    assert response.status_code == 200
    assert "<title>Citationer 仪表板</title>" in response.text


def test_dashboard_assets_load(empty_client: TestClient) -> None:
    assert empty_client.get("/style.css").status_code == 200
    assert empty_client.get("/app.js").status_code == 200
