"""Web 应用基础冒烟测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from citationer.web.app import create_app


def test_app_factory() -> None:
    app = create_app()
    assert app.title == "Citationer"


def test_index_html_served(empty_client: TestClient) -> None:
    response = empty_client.get("/")
    assert response.status_code == 200
    assert "Citationer 仪表板" in response.text


def test_404_on_unknown(empty_client: TestClient) -> None:
    response = empty_client.get("/not-a-page")
    assert response.status_code == 404


def test_x_frame_options_is_deny(empty_client: TestClient) -> None:
    response = empty_client.get("/")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_cors_allows_localhost_origin(empty_client: TestClient) -> None:
    response = empty_client.get(
        "/", headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8000"


def test_cors_blocks_foreign_origin(empty_client: TestClient) -> None:
    response = empty_client.get(
        "/", headers={"Origin": "https://evil.example.com"}
    )
    assert "access-control-allow-origin" not in response.headers
