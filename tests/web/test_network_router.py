"""network Web 路由测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_keywords_endpoint(web_client: TestClient) -> None:
    response = web_client.get("/api/network/keywords?top_n=10&threshold=1")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        data = response.json()
        assert "keywords" in data or "total_keywords" in data


def test_coauthors_endpoint(web_client: TestClient) -> None:
    response = web_client.get("/api/network/coauthors?min_papers=1")
    assert response.status_code in (200, 501)


def test_cocitation_endpoint(web_client: TestClient) -> None:
    response = web_client.get("/api/network/cocitation?top_n=10")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        data = response.json()
        assert "edges" in data or "total_edges" in data


def test_coupling_endpoint(web_client: TestClient) -> None:
    response = web_client.get("/api/network/coupling?top_n=10")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        data = response.json()
        assert "edges" in data or "total_edges" in data
