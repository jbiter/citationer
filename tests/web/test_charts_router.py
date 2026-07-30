"""图表 Web 路由测试。"""

from __future__ import annotations

import builtins
import sys

import matplotlib
import pytest
from fastapi.testclient import TestClient

matplotlib.use("Agg")


def test_yearly_chart(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/yearly.png")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        assert response.headers["content-type"] == "image/png"


def test_yearly_chart_cumulative(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/yearly.png?cumulative=true")
    assert response.status_code in (200, 501)


def test_top_chart_journals(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/top/journals.png?top=3")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        assert response.headers["content-type"] == "image/png"


def test_top_chart_authors(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/top/authors.png?top=3")
    assert response.status_code in (200, 501)


def test_top_chart_institutions(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/top/institutions.png?top=3")
    assert response.status_code in (200, 501)


def test_network_keywords_html(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/network/keywords.html?top_n=10")
    assert response.status_code in (200, 501)
    if response.status_code == 200:
        assert "text/html" in response.headers["content-type"]


def test_network_coauthors_html(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/network/coauthors.html")
    assert response.status_code in (200, 501)


def test_network_cocitation_html(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/network/cocitation.html?top_n=10")
    assert response.status_code in (200, 501)


def test_network_coupling_html(web_client: TestClient) -> None:
    response = web_client.get("/api/charts/network/coupling.html?top_n=10")
    assert response.status_code in (200, 501)


def test_charts_return_501_without_viz_extras(
    web_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """模拟缺少 viz extras 时，图表端点返回 501。"""
    original_import = builtins.__import__

    def _restricted_import(name: str, *args: object, **kwargs: object):
        if name in {"citationer.viz", "citationer.viz.charts"}:
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _restricted_import)

    # 强制下次请求重新 import 图表模块，以便 monkeypatch 生效
    for mod in list(sys.modules):
        if mod == "citationer.viz" or mod.startswith("citationer.viz."):
            del sys.modules[mod]

    paths = [
        "/api/charts/yearly.png",
        "/api/charts/top/journals.png?top=3",
        "/api/charts/top/authors.png?top=3",
        "/api/charts/top/institutions.png?top=3",
    ]
    for path in paths:
        response = web_client.get(path)
        assert response.status_code == 501
        assert "viz" in response.json()["detail"]


def test_charts_return_501_without_network_extras(
    web_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """模拟缺少 [network] extras 时，网络图端点返回 501。"""
    original_import = builtins.__import__

    def _restricted_import(name: str, *args: object, **kwargs: object):
        if name == "networkx" or name.startswith("networkx."):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _restricted_import)

    paths = [
        "/api/charts/network/keywords.html?top_n=10",
        "/api/charts/network/coauthors.html",
        "/api/charts/network/cocitation.html?top_n=10",
        "/api/charts/network/coupling.html?top_n=10",
    ]
    for path in paths:
        response = web_client.get(path)
        assert response.status_code == 501
        assert "[network]" in response.json()["detail"]
