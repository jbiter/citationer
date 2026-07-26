"""network Web 路由测试。"""

from __future__ import annotations

import builtins

import pytest
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


def test_endpoints_return_501_without_network_extras(
    web_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """模拟缺少 [network] extras 时，所有 network 端点返回 501。"""
    original_import = builtins.__import__

    def _restricted_import(name: str, *args: object, **kwargs: object):
        if name == "networkx" or name.startswith("networkx."):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _restricted_import)

    paths = [
        "/api/network/keywords?top_n=10&threshold=1",
        "/api/network/coauthors?min_papers=1",
        "/api/network/cocitation?top_n=10",
        "/api/network/coupling?top_n=10",
    ]
    for path in paths:
        response = web_client.get(path)
        assert response.status_code == 501
        assert "[network]" in response.json()["detail"]
