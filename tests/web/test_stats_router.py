"""stats Web 路由测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_returns_records_count(web_client: TestClient) -> None:
    response = web_client.get("/api/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 5


def test_yearly_returns_year_counts(web_client: TestClient) -> None:
    response = web_client.get("/api/stats/yearly")
    assert response.status_code == 200
    data = response.json()
    assert "year_counts" in data


def test_journals_top_query_param(web_client: TestClient) -> None:
    response = web_client.get("/api/stats/journals?top=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2


def test_empty_database_returns_400(empty_client: TestClient) -> None:
    response = empty_client.get("/api/stats/overview")
    assert response.status_code == 400
    assert "尚未导入记录" in response.json()["detail"]
