"""compare Web 路由测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_compare_overview(web_client: TestClient) -> None:
    response = web_client.get("/api/compare/overview")
    assert response.status_code == 200
    data = response.json()
    assert "overviews" in data


def test_compare_trends(web_client: TestClient) -> None:
    response = web_client.get("/api/compare/trends")
    assert response.status_code == 200
