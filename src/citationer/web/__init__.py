"""Citationer 本地 Web 服务器包。"""

from __future__ import annotations

try:
    from fastapi import FastAPI  # noqa: F401
except ImportError as exc:  # pragma: no cover
    raise ImportError("Web 服务器需要额外依赖。请安装：pip install 'citationer[web]'") from exc

from citationer.web.app import create_app

__all__ = ["create_app"]
