"""数据管理 Web 路由测试。"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

from citationer.services.data_ops import _run_isolated


def test_status_returns_count(web_client: TestClient) -> None:
    response = web_client.get("/api/data/status")
    assert response.status_code == 200
    assert response.json()["total_records"] == 5


def test_run_isolated_normal_function() -> None:
    def _func(value: list[Any]) -> None:
        value.append(1)

    container: list[Any] = []
    _run_isolated(_func, container)
    assert container == [1]


def test_run_isolated_system_exit_none() -> None:
    def _func() -> None:
        sys.exit()

    _run_isolated(_func)  # should not raise


def test_run_isolated_system_exit_zero() -> None:
    def _func() -> None:
        sys.exit(0)

    _run_isolated(_func)  # should not raise


def test_run_isolated_system_exit_nonzero() -> None:
    def _func() -> None:
        sys.exit(1)

    with pytest.raises(RuntimeError, match="CLI 命令失败"):
        _run_isolated(_func)


def test_run_isolated_captures_stdout_stderr(capsys: pytest.CaptureFixture) -> None:
    def _func() -> None:
        print("stdout message")
        print("stderr message", file=sys.stderr)

    _run_isolated(_func)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_scan_import_error_returns_501(
    web_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _broken() -> None:
        raise ImportError("scan unavailable")

    monkeypatch.setattr("citationer.web.routers.data.run_scan", _broken)
    response = web_client.post("/api/data/scan")
    assert response.status_code == 501
    assert "扫描模块不可用" in response.json()["detail"]


def test_scan_runtime_error_returns_500(
    web_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _broken() -> None:
        raise RuntimeError("scan failed")

    monkeypatch.setattr("citationer.web.routers.data.run_scan", _broken)
    response = web_client.post("/api/data/scan")
    assert response.status_code == 500
    assert "scan failed" in response.json()["detail"]
